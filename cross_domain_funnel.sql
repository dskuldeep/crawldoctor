WITH signup_visitors AS (
    -- 1. Identify users who visited /sign-up on ANY subdomain
    SELECT 
        client_id,
        MIN(timestamp) as first_signup_visit
    FROM public.visits
    WHERE path ~* '^.*/sign-up([/?#]|$)'
    AND client_id IS NOT NULL
    GROUP BY 1
),
signup_completers AS (
    -- 2. Filter to those who reached /company-info on ANY subdomain
    SELECT 
        v.client_id,
        MIN(v.timestamp) as reached_company_info_at
    FROM public.visits v
    JOIN signup_visitors sv ON v.client_id = sv.client_id
    WHERE v.path ~* '^.*/company-info([/?#]|$)'
    AND v.timestamp >= sv.first_signup_visit -- Ensure completion is after signup
    GROUP BY 1
),


-- 3. Session Stitching: Find ALL visits related to these users (by ID or IP+UA Fingerprint)
-- This recovers the "getmaxim.ai" history even if the cross-domain tracking ID was dropped.
related_visits AS (
    -- Matches by Client ID
    SELECT 
        v.client_id as original_client_id, -- Keep track of which ID owns the visit
        sc.client_id as unified_client_id, -- The 'Master' ID (the converter)
        v.*
    FROM public.visits v
    JOIN signup_completers sc ON v.client_id = sc.client_id
    
    UNION ALL
    
    -- Matches by IP + User Agent (within 24 hours) - Excluding visits already found by ID
    SELECT 
        v.client_id as original_client_id,
        sc.client_id as unified_client_id,
        v.*
    FROM signup_completers sc
    JOIN public.visits target_v ON target_v.client_id = sc.client_id
    JOIN public.visits v ON v.ip_address = target_v.ip_address 
                        AND v.user_agent = target_v.user_agent
    WHERE v.timestamp BETWEEN target_v.timestamp - INTERVAL '24 hours' AND target_v.timestamp
      AND v.client_id IS DISTINCT FROM sc.client_id
),
user_attribution AS (
    -- 4. Find original source (First ever visit in the stitched history)
    SELECT DISTINCT ON (unified_client_id)
        unified_client_id as client_id,
        referrer as original_referrer,
        source as original_utm_source,
        medium as original_utm_medium,
        timestamp as first_ever_visit
    FROM related_visits
    ORDER BY unified_client_id, timestamp ASC
),
user_journey_paths AS (
    -- 5. Construct the full user journey path using Stitched Visits
    SELECT 
        unified_client_id as client_id,
        STRING_AGG(path || ' (' || page_domain || ')', ' → ' ORDER BY timestamp ASC) as full_journey_path
    FROM related_visits
    WHERE timestamp <= (SELECT reached_company_info_at FROM signup_completers WHERE client_id = related_visits.unified_client_id)
    GROUP BY 1
),
signup_data AS (
    -- 6. Extract ALL data from sign-up page (URL params AND Form Events)
    SELECT 
        unified_client_id as client_id,
        STRING_AGG(DISTINCT (
            SELECT STRING_AGG(key || ': ' || (value->>0), ' | ') 
            FROM json_each(query_params)
            WHERE key NOT IN ('utm_source', 'utm_medium', 'utm_campaign', 'd', 'tid', 'ref')
        ), ' || ') as signup_url_params,
        
        json_agg(event_data ORDER BY timestamp ASC) FILTER (WHERE event_data IS NOT NULL)::text as signup_form_submission
    FROM (
        -- Combine Visits (for params)
        SELECT 
            unified_client_id, 
            query_params, 
            NULL::json as event_data, 
            timestamp
        FROM related_visits
        WHERE path ~* '^.*/sign-up([/?#]|$)'
        
        UNION ALL
        
        -- Get Events (join events to related visits)
        SELECT 
            rv.unified_client_id, 
            NULL as query_params, 
            e.event_data, 
            e.timestamp
        FROM public.visit_events e
        JOIN related_visits rv ON e.visit_id = rv.id
        WHERE e.path ~* '^.*/sign-up.*' AND e.event_type IN ('form_submit', 'custom', 'click', 'form_start')
    ) as combined_signup_data
    GROUP BY unified_client_id
),
company_info_full_data AS (
    -- 7. Capture ALL data from company-info page
    SELECT 
        unified_client_id as client_id,
        STRING_AGG(DISTINCT (
            SELECT STRING_AGG(key || ': ' || (value->>0), ' | ') 
            FROM json_each(query_params)
            WHERE key NOT IN ('utm_source', 'utm_medium', 'utm_campaign', 'd', 'tid')
        ), ' || ') as company_info_params,
        
        json_agg(event_data ORDER BY timestamp ASC) FILTER (WHERE event_data IS NOT NULL)::text as company_info_form_submission
    FROM (
        SELECT 
            unified_client_id, 
            query_params, 
            NULL::json as event_data, 
            timestamp
        FROM related_visits
        WHERE path ~* '^.*/company-info([/?#]|$)'
        
        UNION ALL
        
        SELECT 
            rv.unified_client_id, 
            NULL as query_params, 
            e.event_data, 
            e.timestamp
        FROM public.visit_events e
        JOIN related_visits rv ON e.visit_id = rv.id
        WHERE e.path ~* '^.*/company-info.*' AND e.event_type IN ('form_submit', 'custom', 'click', 'form_start')
    ) as combined_company_data
    GROUP BY unified_client_id
)
SELECT 
    sc.client_id as unique_user_key,
    
    -- Full Journey (Stitched)
    ujp.full_journey_path,

    -- Sign-up Page Data
    COALESCE(sud.signup_url_params, 'No URL params') as signup_page_params,
    COALESCE(sud.signup_form_submission, 'No form data') as raw_signup_events,
    
    -- Attempt to extract email from raw events (Generic Email Regex)
    substring(sud.signup_form_submission from '([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})') as potentially_extracted_email,
    
    -- Captured Info (Company Info Page)
    COALESCE(cifd.company_info_params, 'No URL params') as company_info_url_params,
    COALESCE(cifd.company_info_form_submission, 'No form data') as company_info_form_data,
    
    -- Attribution (Earliest touch in stitched history)
    ua.original_referrer,
    ua.original_utm_source,
    ua.original_utm_medium,
    
    -- Journey Timing
    ua.first_ever_visit AT TIME ZONE 'UTC' as user_acquired_at,
    sv.first_signup_visit AT TIME ZONE 'UTC' as signup_visited_at,
    sc.reached_company_info_at AT TIME ZONE 'UTC' as company_info_completed_at,
    
    -- Durations
    (sc.reached_company_info_at - ua.first_ever_visit) as total_time_to_complete,
    (sc.reached_company_info_at - sv.first_signup_visit) as time_in_funnel

FROM signup_completers sc
JOIN signup_visitors sv ON sc.client_id = sv.client_id
LEFT JOIN user_attribution ua ON sc.client_id = ua.client_id
LEFT JOIN user_journey_paths ujp ON sc.client_id = ujp.client_id
LEFT JOIN signup_data sud ON sc.client_id = sud.client_id
LEFT JOIN company_info_full_data cifd ON sc.client_id = cifd.client_id
ORDER BY company_info_completed_at DESC;
