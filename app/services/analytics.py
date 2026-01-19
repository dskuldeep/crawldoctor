"""Simplified analytics service for visitor categorization and page tracking."""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
import structlog
import time

from app.models.visit import Visit, VisitSession, VisitEvent
from app.config import settings

logger = structlog.get_logger()


class AnalyticsService:
    """Simplified analytics service for visitor insights."""
    
    def get_visitor_summary(
        self,
        db: Session,
        days: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get summary of visitors by category."""
        if start_date or end_date:
            since = start_date or (datetime.now() - timedelta(days=days))
            until = end_date
        else:
            since = datetime.now() - timedelta(days=days)
            until = None
        
        # Get visits by category - simplified approach
        ai_crawlers_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == True
        )
        if until:
            ai_crawlers_query = ai_crawlers_query.filter(Visit.timestamp <= until)
        ai_crawlers = ai_crawlers_query.scalar() or 0
        
        mobile_humans_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == False,
            Visit.user_agent.ilike('%mobile%')
        )
        if until:
            mobile_humans_query = mobile_humans_query.filter(Visit.timestamp <= until)
        mobile_humans = mobile_humans_query.scalar() or 0
        
        desktop_humans_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == False,
            ~Visit.user_agent.ilike('%mobile%')
        )
        if until:
            desktop_humans_query = desktop_humans_query.filter(Visit.timestamp <= until)
        desktop_humans = desktop_humans_query.scalar() or 0
        
        visits_by_category = [
            {'category': 'AI Crawlers', 'count': ai_crawlers},
            {'category': 'Mobile Humans', 'count': mobile_humans},
            {'category': 'Desktop Humans', 'count': desktop_humans}
        ]
        
        # Get total visits
        total_visits_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since
        )
        if until:
            total_visits_query = total_visits_query.filter(Visit.timestamp <= until)
        total_visits = total_visits_query.scalar() or 0
        
        # Get unique visitors (sessions)
        unique_visitors_query = db.query(func.count(VisitSession.id)).filter(
            VisitSession.last_visit >= since
        )
        if until:
            unique_visitors_query = unique_visitors_query.filter(VisitSession.last_visit <= until)
        unique_visitors = unique_visitors_query.scalar() or 0
        
        # Get top user agents
        top_user_agents_query = db.query(
            Visit.user_agent,
            func.count(Visit.id).label('count')
        ).filter(
            Visit.timestamp >= since
        )
        if until:
            top_user_agents_query = top_user_agents_query.filter(Visit.timestamp <= until)
        top_user_agents = top_user_agents_query.group_by(Visit.user_agent).order_by(
            desc('count')
        ).limit(10).all()
        
        return {
            "total_visits": total_visits,
            "unique_visitors": unique_visitors,
            "visits_by_category": visits_by_category,
            "top_user_agents": [
                {"user_agent": row.user_agent[:100], "count": row.count}
                for row in top_user_agents
            ],
            "period_days": days
        }
    
    def get_page_analytics(
        self,
        db: Session,
        days: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get analytics by page."""
        if start_date or end_date:
            since = start_date or (datetime.now() - timedelta(days=days))
            until = end_date
        else:
            since = datetime.now() - timedelta(days=days)
            until = None
        
        # Get visits by page domain
        page_visits_query = db.query(
            Visit.page_domain,
            func.count(Visit.id).label('count'),
            func.count(func.distinct(Visit.session_id)).label('unique_visitors')
        ).filter(
            Visit.timestamp >= since,
            Visit.page_domain.isnot(None)
        )
        if until:
            page_visits_query = page_visits_query.filter(Visit.timestamp <= until)
        page_visits = page_visits_query.group_by(Visit.page_domain).order_by(
            desc('count')
        ).limit(20).all()
        
        # Get crawler visits by page
        crawler_visits_query = db.query(
            Visit.page_domain,
            Visit.crawler_type,
            func.count(Visit.id).label('count')
        ).filter(
            Visit.timestamp >= since,
            Visit.is_bot == True,
            Visit.page_domain.isnot(None)
        )
        if until:
            crawler_visits_query = crawler_visits_query.filter(Visit.timestamp <= until)
        crawler_visits = crawler_visits_query.group_by(Visit.page_domain, Visit.crawler_type).order_by(
            desc('count')
        ).limit(20).all()
        
        return {
            "page_visits": [
                {
                    "domain": row.page_domain,
                    "total_visits": row.count,
                    "unique_visitors": row.unique_visitors
                }
                for row in page_visits
            ],
            "crawler_visits": [
                {
                    "domain": row.page_domain,
                    "crawler": row.crawler_type,
                    "count": row.count
                }
                for row in crawler_visits
            ],
            "period_days": days
        }
    
    def get_recent_activity(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Get recent visitor activity with pagination - optimized for large datasets with retry logic."""
        from sqlalchemy.orm import joinedload
        
        # Default to last 7 days to avoid full table scans if no range is provided
        if not start_date and not end_date:
            start_date = datetime.now() - timedelta(days=7)
        
        # Try to get data with retries
        for attempt in range(max_retries):
            try:
                # Use indexed timestamp for fast counting - limit to recent data only
                # For very large DBs, estimate count for better performance
                query = db.query(Visit).options(joinedload(Visit.session)).order_by(desc(Visit.timestamp))
                if start_date:
                    query = query.filter(Visit.timestamp >= start_date)
                if end_date:
                    query = query.filter(Visit.timestamp <= end_date)

                if offset == 0:
                    # Only get exact count on first page
                    total_count = query.order_by(None).with_entities(func.count(Visit.id)).scalar() or 0
                else:
                    # For subsequent pages, use cached estimate (10x faster)
                    total_count = offset + limit + 1000  # Rough estimate
                
                # Optimized query: eager load session to prevent N+1 queries
                recent_visits = query.offset(offset).limit(limit).all()
                
                visits_data = []
                for visit in recent_visits:
                    # Fallback to session geo if visit geo is missing
                    country = visit.country
                    city = visit.city
                    if not country and visit.session:
                        country = visit.session.country
                        city = visit.session.city
                    
                    visits_data.append({
                        "id": visit.id,
                        "timestamp": visit.timestamp.isoformat() if visit.timestamp else None,
                        "user_agent": visit.user_agent or "",
                        "page_url": visit.page_url or "",
                        "is_bot": visit.is_bot or False,
                        "crawler_type": visit.crawler_type or "",
                        "country": country or "",
                        "city": city or "",
                        "session_id": visit.session_id or "",
                        "tracking_id": visit.tracking_id or "",
                        "source": visit.source or "",
                        "medium": visit.medium or "",
                        "campaign": visit.campaign or "",
                        # Client-side captured data
                        "client_side_timezone": visit.client_side_timezone or "",
                        "client_side_language": visit.client_side_language or "",
                        "client_side_screen_resolution": visit.client_side_screen_resolution or "",
                        "client_side_viewport_size": visit.client_side_viewport_size or "",
                        "client_side_device_memory": visit.client_side_device_memory or "",
                        "client_side_connection_type": visit.client_side_connection_type or ""
                    })
                
                return {
                    "visits": visits_data,
                    "total_count": total_count,
                    "has_next": (offset + limit) < total_count,
                    "has_prev": offset > 0,
                    "current_page": (offset // limit) + 1,
                    "total_pages": ((total_count - 1) // limit) + 1 if total_count > 0 else 0
                }
            except (OperationalError, SQLTimeoutError) as e:
                logger.warning(f"Recent activity query timeout, attempt {attempt + 1}/{max_retries}", error=str(e), offset=offset)
                db.rollback()
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Quick retry with backoff
                else:
                    logger.error("Failed to get recent activity after retries", error=str(e))
                    # Return empty result on final failure
                    return {
                        "visits": [],
                        "total_count": 0,
                        "has_next": False,
                        "has_prev": False,
                        "current_page": 1,
                        "total_pages": 0,
                        "error": "Database timeout - please try again or reduce page size"
                    }
            except Exception as e:
                logger.error("Error in get_recent_activity", error=str(e))
                # Return empty result on other errors
                return {
                    "visits": [],
                    "total_count": 0,
                    "has_next": False,
                    "has_prev": False,
                    "current_page": 1,
                    "total_pages": 0,
                    "error": str(e)
                }
        
        # Should never reach here, but just in case
        return {
            "visits": [],
            "total_count": 0,
            "has_next": False,
            "has_prev": False,
            "current_page": 1,
            "total_pages": 0
        }

    def list_sessions(self, db: Session, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List sessions with summary info - OPTIMIZED for large datasets."""
        try:
            # Fast count with estimation for pagination
            if offset == 0:
                total = db.query(func.count(VisitSession.id)).scalar() or 0
            else:
                total = offset + limit + 100  # Estimate for speed
            
            # Single optimized query with only what we need
            sessions = db.query(VisitSession).order_by(desc(VisitSession.last_visit)).offset(offset).limit(limit).all()
            
            # Batch-fetch all visit data for these sessions in ONE query (massive speedup)
            session_ids = [s.id for s in sessions]
            if session_ids:
                # Get visit counts per session in one query
                visit_counts = dict(
                    db.query(Visit.session_id, func.count(Visit.id))
                    .filter(Visit.session_id.in_(session_ids))
                    .group_by(Visit.session_id)
                    .all()
                )
                
                # Get bot classification per session in one query
                bot_classifications = {}
                bot_data = db.query(
                    Visit.session_id, 
                    Visit.is_bot,
                    func.count(Visit.id).label('count')
                ).filter(Visit.session_id.in_(session_ids)).group_by(Visit.session_id, Visit.is_bot).all()
                
                for session_id, is_bot, count in bot_data:
                    if session_id not in bot_classifications or count > bot_classifications[session_id][1]:
                        bot_classifications[session_id] = (is_bot, count)
            else:
                visit_counts = {}
                bot_classifications = {}
            
            data = []
            for s in sessions:
                # Use cached session geo data (already populated during tracking)
                sess_country = s.country or ""
                sess_city = s.city or ""
                
                # Use batch-fetched data instead of per-session queries
                visit_count = visit_counts.get(s.id, 0)
                is_bot_session = bot_classifications.get(s.id, (None, 0))[0]
                
                crawler_label = None
                if is_bot_session is True:
                    crawler_label = 'AI Crawler'
                elif is_bot_session is False:
                    crawler_label = 'Human'

                data.append({
                    "session_id": s.id,
                    "client_id": s.client_id,
                    "first_visit": s.first_visit.isoformat() if s.first_visit else None,
                    "last_visit": s.last_visit.isoformat() if s.last_visit else None,
                    "visit_count": visit_count,
                    "ip_address": s.ip_address or "",
                    "country": sess_country,
                    "city": sess_city,
                    "classification": crawler_label or "Unknown",
                    # Client-side captured data
                    "client_side_timezone": s.client_side_timezone or "",
                    "client_side_language": s.client_side_language or "",
                    "client_side_screen_resolution": s.client_side_screen_resolution or "",
                    "client_side_viewport_size": s.client_side_viewport_size or "",
                    "client_side_device_memory": s.client_side_device_memory or "",
                    "client_side_connection_type": s.client_side_connection_type or ""
                })
            return {
                "sessions": data,
                "total_count": total,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "current_page": (offset // limit) + 1,
                "total_pages": ((total - 1) // limit) + 1 if total > 0 else 0
            }
        except Exception as e:
            logger.error("Error in list_sessions", error=str(e))
            return {
                "sessions": [],
                "total_count": 0,
                "has_next": False,
                "has_prev": False,
                "current_page": 1,
                "total_pages": 0
            }

    def get_session_detail(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Get a session with all visits and events in chronological order."""
        session = db.query(VisitSession).filter(VisitSession.id == session_id).first()
        if not session:
            return {"error": "not_found"}

        visits = db.query(Visit).filter(Visit.session_id == session_id).order_by(Visit.timestamp.asc()).all()
        events = db.query(VisitEvent).filter(VisitEvent.session_id == session_id).order_by(VisitEvent.timestamp.asc()).all()

        visits_json = [
            {
                "id": v.id,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                "page_url": v.page_url,
                "referrer": v.referrer,
                "path": v.path,
                "source": v.source,
                "medium": v.medium,
                "campaign": v.campaign,
                "tracking_id": v.tracking_id,
                "is_bot": v.is_bot,
                "crawler_type": v.crawler_type,
                # Client-side captured data
                "client_side_timezone": v.client_side_timezone or "",
                "client_side_language": v.client_side_language or "",
                "client_side_screen_resolution": v.client_side_screen_resolution or "",
                "client_side_viewport_size": v.client_side_viewport_size or "",
                "client_side_device_memory": v.client_side_device_memory or "",
                "client_side_connection_type": v.client_side_connection_type or ""
            }
            for v in visits
        ]

        # Create a mapping of visit IDs to visits for efficient lookup
        visits_dict = {v.id: v for v in visits}

        # Process events with enhanced location fallback logic and debugging
        events_json = []
        for e in events:
            # Try to get location from multiple sources (priority: Visit -> Session -> event_data)
            country = None
            city = None
            location_source = "none"

            # First try Visit table (if event is linked to a visit)
            if e.visit_id and e.visit_id in visits_dict:
                visit = visits_dict[e.visit_id]
                if visit.country and visit.country != "XX":
                    country = visit.country
                    city = visit.city
                    location_source = "visit"
                elif visit.country == "XX":
                    # Visit has XX, try session instead
                    if session and session.country and session.country != "XX":
                        country = session.country
                        city = session.city
                        location_source = "session"

            # If not in Visit, try Session table directly
            if not country and session:
                if session.country and session.country != "XX":
                    country = session.country
                    city = session.city
                    location_source = "session"

            # Fallback to event_data JSON (legacy/backup) - but only if it's not XX
            if not country and e.event_data:
                event_country = e.event_data.get("country")
                if event_country and event_country != "XX":
                    country = event_country
                    city = e.event_data.get("city")
                    location_source = "event_data"

            # Final fallback: if we still don't have country but event_data has XX, use session or visit XX
            if not country and e.event_data and e.event_data.get("country") == "XX":
                # Use XX from event_data, but prefer session/visit if available
                if session and session.country:
                    country = session.country  # Even if it's XX, it's more accurate
                    city = session.city
                    location_source = "session_xx"
                elif e.visit_id and e.visit_id in visits_dict:
                    visit = visits_dict[e.visit_id]
                    if visit.country:
                        country = visit.country
                        city = visit.city
                        location_source = "visit_xx"

            # If we still don't have anything, use the original event_data XX
            if not country and e.event_data:
                country = e.event_data.get("country")
                city = e.event_data.get("city")
                location_source = "event_data_xx"

            # Log for debugging (only in development)
            if settings.debug and (country == "XX" or not country):
                logger.warning(
                    "Event location fallback",
                    event_id=e.id,
                    visit_id=e.visit_id,
                    session_id=e.session_id,
                    session_country=session.country if session else None,
                    visit_country=visits_dict[e.visit_id].country if e.visit_id and e.visit_id in visits_dict else None,
                    event_country=e.event_data.get("country") if e.event_data else None,
                    final_country=country,
                    location_source=location_source
                )

            events_json.append({
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "event_type": e.event_type,
                "page_url": e.page_url,
                "referrer": e.referrer,
                "path": e.path,
                "page_domain": e.page_domain,
                "referrer_domain": e.referrer_domain,
                "country": country,
                "city": city,
                "source": e.source or (e.event_data or {}).get("source"),
                "medium": e.medium or (e.event_data or {}).get("medium"),
                "campaign": e.campaign or (e.event_data or {}).get("campaign"),
                "tracking_id": e.tracking_id or (e.event_data or {}).get("tracking_id"),
                "tracking_method": (e.event_data or {}).get("tracking_method"),
                "crawler_type": (e.event_data or {}).get("crawler_type"),
                "is_bot": (e.event_data or {}).get("is_bot"),
                "data": e.event_data,
                "visit_id": e.visit_id,
                "_debug_location_source": location_source if settings.debug else None,
                # Client-side captured data
                "client_side_timezone": e.client_side_timezone or "",
                "client_side_language": e.client_side_language or "",
                "client_side_screen_resolution": e.client_side_screen_resolution or "",
                "client_side_viewport_size": e.client_side_viewport_size or "",
                "client_side_device_memory": e.client_side_device_memory or "",
                "client_side_connection_type": e.client_side_connection_type or ""
            })

        # Timeline: merge visits and events
        timeline = [
            {"type": "visit", **vj} for vj in visits_json
        ] + [
            {"type": "event", **ej} for ej in events_json
        ]
        timeline.sort(key=lambda x: x.get("timestamp") or "")

        return {
            "session": {
                "session_id": session.id,
                "client_id": session.client_id,
                "ip_address": session.ip_address,
                "first_visit": session.first_visit.isoformat() if session.first_visit else None,
                "last_visit": session.last_visit.isoformat() if session.last_visit else None,
                "country": session.country,
                "city": session.city,
                "visit_count": session.visit_count,
                # Client-side captured data
                "client_side_timezone": session.client_side_timezone or "",
                "client_side_language": session.client_side_language or "",
                "client_side_screen_resolution": session.client_side_screen_resolution or "",
                "client_side_viewport_size": session.client_side_viewport_size or "",
                "client_side_device_memory": session.client_side_device_memory or "",
                "client_side_connection_type": session.client_side_connection_type or ""
            },
            "visits": visits_json,
            "events": events_json,
            "timeline": timeline,
        }

    def get_all_visits_for_export(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, batch_size: int = None, max_retries: int = 3):
        """Get visits for CSV export with optional date filtering.
        
        Uses a generator pattern with optimized queries to avoid connection timeouts.
        Includes retry logic for reliability and smaller batches for memory efficiency.
        """
        if batch_size is None:
            batch_size = settings.analytics_export_batch_size
        
        # Build base query with optional date filtering
        query = db.query(Visit)
        if start_date:
            query = query.filter(Visit.timestamp >= start_date)
        if end_date:
            query = query.filter(Visit.timestamp <= end_date)
        
        # Get total count first with retry logic
        total_count = 0
        for attempt in range(max_retries):
            try:
                total_count = query.count() or 0
                break
            except (OperationalError, SQLTimeoutError) as e:
                logger.warning(f"Count query timeout, attempt {attempt + 1}/{max_retries}", error=str(e))
                if attempt == max_retries - 1:
                    logger.error("Failed to get count after retries, using estimation")
                    # Try to estimate based on a simple query
                    try:
                        total_count = db.query(func.count(Visit.id)).scalar() or 0
                    except:
                        total_count = 1000000  # Rough estimate if all else fails
                db.rollback()
                time.sleep(1 * (attempt + 1))  # Exponential backoff
        
        logger.info(f"Starting export of {total_count} visits in batches of {batch_size}")
        
        # Process in smaller batches with retry logic
        offset = 0
        processed = 0
        while offset < total_count:
            retry_count = 0
            batch_success = False
            
            while retry_count < max_retries and not batch_success:
                try:
                    # Get visits without joins first
                    batch = query.order_by(
                        desc(Visit.timestamp)
                    ).offset(offset).limit(batch_size).all()
                    
                    if not batch:
                        batch_success = True
                        break
                    
                    # Batch fetch sessions for visits that might need location data
                    session_ids = list(set([v.session_id for v in batch if v.session_id and not v.country]))
                    sessions_dict = {}
                    if session_ids:
                        sessions = db.query(VisitSession).filter(
                            VisitSession.id.in_(session_ids)
                        ).all()
                        sessions_dict = {s.id: s for s in sessions}
                        
                    for visit in batch:
                        # Get location from Visit first, fallback to Session
                        country = visit.country
                        city = visit.city
                        
                        if not country and visit.session_id in sessions_dict:
                            session = sessions_dict[visit.session_id]
                            country = session.country
                            city = session.city
                        
                        yield {
                            "id": visit.id,
                            "timestamp": visit.timestamp.isoformat() if visit.timestamp else "",
                            "session_id": visit.session_id or "",
                            "user_agent": visit.user_agent or "",
                            "page_url": visit.page_url or "",
                            "page_domain": visit.page_domain or "",
                            "path": visit.path or "",
                            "is_bot": str(visit.is_bot) if visit.is_bot is not None else "",
                            "crawler_type": visit.crawler_type or "",
                            "country": country or "",
                            "city": city or "",
                            "tracking_id": visit.tracking_id or "",
                            "source": visit.source or "",
                            "medium": visit.medium or "",
                            "campaign": visit.campaign or "",
                            "referrer": visit.referrer or "",
                            "page_title": visit.page_title or "",
                            "request_method": visit.request_method or "",
                            "response_status": str(visit.response_status) if visit.response_status is not None else "",
                            "ip_address": visit.ip_address or "",
                            # Client-side captured data
                            "client_side_timezone": visit.client_side_timezone or "",
                            "client_side_language": visit.client_side_language or "",
                            "client_side_screen_resolution": visit.client_side_screen_resolution or "",
                            "client_side_viewport_size": visit.client_side_viewport_size or "",
                            "client_side_device_memory": visit.client_side_device_memory or "",
                            "client_side_connection_type": visit.client_side_connection_type or ""
                        }
                    
                    processed += len(batch)
                    logger.info(f"Exported batch: {processed}/{total_count} visits")
                    
                    batch_success = True
                    
                except (OperationalError, SQLTimeoutError) as e:
                    retry_count += 1
                    logger.warning(f"Export batch timeout at offset {offset}, attempt {retry_count}/{max_retries}", error=str(e))
                    db.rollback()
                    if retry_count < max_retries:
                        time.sleep(1 * retry_count)  # Exponential backoff
                    else:
                        logger.error(f"Failed to export batch at offset {offset} after {max_retries} retries")
                        raise
            
            offset += batch_size
            # Clear the session to free memory
            db.expire_all()
        
        logger.info(f"Export complete: {processed} visits exported")

    def get_all_events_for_export(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, batch_size: int = None, max_retries: int = 3):
        """Get visit events for CSV export with optional date filtering.
        
        Uses a generator pattern with optimized queries to avoid connection timeouts.
        Includes retry logic for reliability and smaller batches for memory efficiency.
        """
        import json
        
        if batch_size is None:
            batch_size = settings.analytics_export_batch_size
        
        # Build base query with optional date filtering
        query = db.query(VisitEvent)
        if start_date:
            query = query.filter(VisitEvent.timestamp >= start_date)
        if end_date:
            query = query.filter(VisitEvent.timestamp <= end_date)
        
        # Get total count first with retry logic
        total_count = 0
        for attempt in range(max_retries):
            try:
                total_count = query.count() or 0
                break
            except (OperationalError, SQLTimeoutError) as e:
                logger.warning(f"Event count query timeout, attempt {attempt + 1}/{max_retries}", error=str(e))
                if attempt == max_retries - 1:
                    logger.error("Failed to get event count after retries, using estimation")
                    try:
                        total_count = db.query(func.count(VisitEvent.id)).scalar() or 0
                    except:
                        total_count = 500000  # Rough estimate if all else fails
                db.rollback()
                time.sleep(1 * (attempt + 1))
        
        logger.info(f"Starting export of {total_count} events in batches of {batch_size}")
        
        # Process in smaller batches with retry logic
        offset = 0
        processed = 0
        while offset < total_count:
            retry_count = 0
            batch_success = False
            
            while retry_count < max_retries and not batch_success:
                try:
                    # Get events without joins first (much faster)
                    events = query.order_by(
                        desc(VisitEvent.timestamp)
                    ).offset(offset).limit(batch_size).all()
                    
                    if not events:
                        batch_success = True
                        break
                    
                    # Batch fetch related data instead of using joins (much faster)
                    session_ids = list(set([ev.session_id for ev in events if ev.session_id]))
                    visit_ids = list(set([ev.visit_id for ev in events if ev.visit_id]))
                    
                    # Fetch sessions and visits in bulk
                    sessions_dict = {}
                    if session_ids:
                        sessions = db.query(VisitSession).filter(
                            VisitSession.id.in_(session_ids)
                        ).all()
                        sessions_dict = {s.id: s for s in sessions}
                    
                    visits_dict = {}
                    if visit_ids:
                        visits = db.query(Visit).filter(
                            Visit.id.in_(visit_ids)
                        ).all()
                        visits_dict = {v.id: v for v in visits}
                    
                    # Now process events with cached data - enhanced location fallback logic
                    for ev in events:
                        # Try to get location from multiple sources (priority: Visit -> Session -> event_data)
                        country = None
                        city = None
                        location_source = "none"

                        # First try Visit table (if event is linked to a visit)
                        if ev.visit_id and ev.visit_id in visits_dict:
                            visit = visits_dict[ev.visit_id]
                            if visit.country and visit.country != "XX":
                                country = visit.country
                                city = visit.city
                                location_source = "visit"
                            elif visit.country == "XX":
                                # Visit has XX, try session instead
                                if ev.session_id in sessions_dict:
                                    session = sessions_dict[ev.session_id]
                                    if session.country and session.country != "XX":
                                        country = session.country
                                        city = session.city
                                        location_source = "session"

                        # If not in Visit, try Session table directly
                        if not country and ev.session_id in sessions_dict:
                            session = sessions_dict[ev.session_id]
                            if session.country and session.country != "XX":
                                country = session.country
                                city = session.city
                                location_source = "session"

                        # Fallback to event_data JSON (legacy/backup) - but only if it's not XX
                        if not country and ev.event_data:
                            event_country = ev.event_data.get("country")
                            if event_country and event_country != "XX":
                                country = event_country
                                city = ev.event_data.get("city")
                                location_source = "event_data"

                        # Final fallback: if we still don't have country but event_data has XX, use session or visit XX
                        if not country and ev.event_data and ev.event_data.get("country") == "XX":
                            # Use XX from event_data, but prefer session/visit if available
                            if ev.session_id in sessions_dict:
                                session = sessions_dict[ev.session_id]
                                if session.country:
                                    country = session.country  # Even if it's XX, it's more accurate
                                    city = session.city
                                    location_source = "session_xx"
                            elif ev.visit_id and ev.visit_id in visits_dict:
                                visit = visits_dict[ev.visit_id]
                                if visit.country:
                                    country = visit.country
                                    city = visit.city
                                    location_source = "visit_xx"

                        # If we still don't have anything, use the original event_data XX
                        if not country and ev.event_data:
                            country = ev.event_data.get("country")
                            city = ev.event_data.get("city")
                            location_source = "event_data_xx"

                        # Log problematic events for debugging (only in development)
                        if settings.debug and (country == "XX" or not country):
                            logger.warning(
                                "Event export location fallback",
                                event_id=ev.id,
                                visit_id=ev.visit_id,
                                session_id=ev.session_id,
                                event_country=ev.event_data.get("country") if ev.event_data else None,
                                final_country=country,
                                location_source=location_source
                            )
                        
                        # Safely extract other fields from event_data
                        event_data = ev.event_data or {}
                        source = ev.source or event_data.get("source") or ""
                        medium = ev.medium or event_data.get("medium") or ""
                        campaign = ev.campaign or event_data.get("campaign") or ""
                        crawler_type = event_data.get("crawler_type") or ""
                        is_bot = event_data.get("is_bot")
                        tracking_id = ev.tracking_id or event_data.get("tracking_id") or ""
                        
                        # Serialize event_data as JSON string for CSV (avoid nested dict)
                        data_str = json.dumps(event_data) if event_data else ""
                        
                        yield {
                            "id": ev.id,
                            "timestamp": ev.timestamp.isoformat() if ev.timestamp else "",
                            "session_id": ev.session_id or "",
                            "visit_id": ev.visit_id or "",
                            "event_type": ev.event_type or "",
                            "page_url": ev.page_url or "",
                            "referrer": ev.referrer or "",
                            "path": ev.path or "",
                            "page_domain": ev.page_domain or "",
                            "referrer_domain": ev.referrer_domain or "",
                            "country": country or "",
                            "city": city or "",
                            "source": source,
                            "medium": medium,
                            "campaign": campaign,
                            "tracking_id": tracking_id,
                            "crawler_type": crawler_type,
                            "is_bot": str(is_bot) if is_bot is not None else "",
                            "event_data_json": data_str,
                            # Client-side captured data
                            "client_side_timezone": ev.client_side_timezone or "",
                            "client_side_language": ev.client_side_language or "",
                            "client_side_screen_resolution": ev.client_side_screen_resolution or "",
                            "client_side_viewport_size": ev.client_side_viewport_size or "",
                            "client_side_device_memory": ev.client_side_device_memory or "",
                            "client_side_connection_type": ev.client_side_connection_type or ""
                        }
                    
                    processed += len(events)
                    logger.info(f"Exported batch: {processed}/{total_count} events")
                    
                    batch_success = True
                    
                except (OperationalError, SQLTimeoutError) as e:
                    retry_count += 1
                    logger.warning(f"Export events batch timeout at offset {offset}, attempt {retry_count}/{max_retries}", error=str(e))
                    db.rollback()
                    if retry_count < max_retries:
                        time.sleep(1 * retry_count)
                    else:
                        logger.error(f"Failed to export events batch at offset {offset} after {max_retries} retries")
                        raise
            
            offset += batch_size
            # Clear the session to free memory
            db.expire_all()
        
        logger.info(f"Events export complete: {processed} events exported")

    def backfill_event_locations(self, db: Session, batch_size: int = 1000) -> Dict[str, Any]:
        """Backfill missing location data in events from their visits and sessions."""
        try:
            # Get events that have XX or missing location data
            events_needing_update = db.query(VisitEvent).filter(
                VisitEvent.event_data.isnot(None),
                db.or_(
                    VisitEvent.event_data["country"].astext == "XX",
                    VisitEvent.event_data["country"].is_(None)
                )
            ).all()

            if not events_needing_update:
                return {
                    "success": True,
                    "updated_events": 0,
                    "message": "No events need location backfilling"
                }

            total_to_update = len(events_needing_update)
            updated_count = 0

            logger.info(f"Starting backfill of {total_to_update} events with missing/XX location data")

            # Get all visit and session IDs for batch processing
            visit_ids = list(set([e.visit_id for e in events_needing_update if e.visit_id]))
            session_ids = list(set([e.session_id for e in events_needing_update if e.session_id]))

            # Batch fetch visits and sessions
            visits_dict = {}
            if visit_ids:
                visits = db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
                visits_dict = {v.id: v for v in visits}

            sessions_dict = {}
            if session_ids:
                sessions = db.query(VisitSession).filter(VisitSession.id.in_(session_ids)).all()
                sessions_dict = {s.id: s for s in sessions}

            # Process events and update their location data
            for event in events_needing_update:
                updated = False
                event_data = event.event_data or {}

                # Try to get location from visit first
                if event.visit_id and event.visit_id in visits_dict:
                    visit = visits_dict[event.visit_id]
                    if visit.country and visit.country != "XX":
                        event_data["country"] = visit.country
                        event_data["city"] = visit.city or "Unknown"
                        updated = True

                # Fall back to session if visit didn't have good data
                if not updated and event.session_id in sessions_dict:
                    session = sessions_dict[event.session_id]
                    if session.country and session.country != "XX":
                        event_data["country"] = session.country
                        event_data["city"] = session.city or "Unknown"
                        updated = True

                # Update the event if we found better location data
                if updated:
                    event.event_data = event_data
                    db.add(event)
                    updated_count += 1

            # Commit all changes
            db.commit()

            logger.info(f"Backfilled location data for {updated_count}/{total_to_update} events")

            return {
                "success": True,
                "updated_events": updated_count,
                "total_processed": total_to_update,
                "message": f"Successfully backfilled location data for {updated_count} events"
            }

        except Exception as e:
            db.rollback()
            logger.error("Error backfilling event locations", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to backfill location data: {str(e)}"
            }

    def delete_all_visits(self, db: Session) -> Dict[str, Any]:
        """Delete all visit data, handling foreign key constraints."""
        try:
            # Count visits before deletion
            visit_count = db.query(func.count(Visit.id)).scalar()
            session_count = db.query(func.count(VisitSession.id)).scalar()
            
            # First, let's try a simple approach - delete visits with cascade
            # This should handle foreign keys automatically if they're set up properly
            deleted_visits = db.query(Visit).delete()
            deleted_sessions = db.query(VisitSession).delete()
            
            db.commit()
            
            return {
                "success": True,
                "deleted_visits": deleted_visits,
                "deleted_sessions": deleted_sessions,
                "original_visit_count": visit_count,
                "original_session_count": session_count,
                "message": f"Successfully deleted {deleted_visits} visits and {deleted_sessions} sessions"
            }
            
        except Exception as e:
            # If that fails, try the manual approach
            try:
                db.rollback()
                
                # Manual cleanup approach - delete all possible dependent records first
                dependent_deletions = []
                
                # List of potential dependent tables to clean up
                dependent_tables = [
                    "crawler_visit_logs",  # This is the one causing the error
                    "tracking_events",
                    "crawler_logs", 
                    "analytics_summaries",
                    "visit_events",
                    "crawler_patterns"
                ]
                
                for table in dependent_tables:
                    try:
                        result = db.execute(text(f"DELETE FROM {table}"))
                        count = result.rowcount if hasattr(result, 'rowcount') else 0
                        if count > 0:
                            dependent_deletions.append(f"{table}: {count}")
                        db.commit()
                    except Exception:
                        db.rollback()
                        continue
                
                # Now try to delete visits and sessions
                deleted_visits = db.query(Visit).delete()
                deleted_sessions = db.query(VisitSession).delete()
                db.commit()
                
                return {
                    "success": True,
                    "deleted_visits": deleted_visits,
                    "deleted_sessions": deleted_sessions,
                    "dependent_deletions": dependent_deletions,
                    "message": f"Successfully deleted {deleted_visits} visits, {deleted_sessions} sessions, and dependencies: {', '.join(dependent_deletions) if dependent_deletions else 'none'}"
                }
                
            except Exception as e2:
                try:
                    db.rollback()
                except:
                    pass
                return {
                    "success": False,
                    "error": str(e2),
                    "original_error": str(e),
                    "message": f"Failed to delete data. Original error: {str(e)}. Cleanup error: {str(e2)}"
                }
    
    def backfill_visit_locations(self, db: Session, batch_size: int = 1000) -> Dict[str, Any]:
        """Backfill missing location data in Visits from their Sessions with batch processing."""
        from sqlalchemy.orm import joinedload

        try:
            # Get total count of visits needing update (missing or XX location)
            total_to_update = db.query(func.count(Visit.id)).join(
                VisitSession, Visit.session_id == VisitSession.id
            ).filter(
                db.or_(
                    Visit.country.is_(None),
                    Visit.country == "XX",
                    db.and_(Visit.city.is_(None), VisitSession.city.isnot(None)),
                    db.and_(Visit.city == "Unknown", VisitSession.city.isnot(None))
                )
            ).scalar() or 0

            if total_to_update == 0:
                return {
                    "success": True,
                    "updated_visits": 0,
                    "message": "No visits need location backfilling"
                }

            updated_count = 0
            offset = 0

            # Process in batches to avoid memory issues
            while offset < total_to_update:
                # Get a batch of visits that need updating
                batch = db.query(Visit).options(
                    joinedload(Visit.session)
                ).join(
                    VisitSession, Visit.session_id == VisitSession.id
                ).filter(
                    db.or_(
                        Visit.country.is_(None),
                        Visit.country == "XX",
                        db.and_(Visit.city.is_(None), VisitSession.city.isnot(None)),
                        db.and_(Visit.city == "Unknown", VisitSession.city.isnot(None))
                    )
                ).offset(offset).limit(batch_size).all()

                if not batch:
                    break

                # Update the batch
                for visit in batch:
                    if visit.session:
                        changed = False
                        # Update country if visit has bad data but session has good data
                        if (not visit.country or visit.country == "XX") and visit.session.country and visit.session.country != "XX":
                            visit.country = visit.session.country
                            changed = True

                        # Update city if visit has bad data but session has good data
                        if (not visit.city or visit.city == "Unknown") and visit.session.city and visit.session.city != "Unknown":
                            visit.city = visit.session.city
                            changed = True

                        if changed:
                            db.add(visit)
                            updated_count += 1

                # Commit the batch
                db.commit()
                logger.info(f"Backfilled location for {len(batch)} visits (total: {updated_count}/{total_to_update})")

                offset += batch_size

                # If batch was smaller than batch_size, we're done
                if len(batch) < batch_size:
                    break

            return {
                "success": True,
                "updated_visits": updated_count,
                "total_processed": total_to_update,
                "message": f"Successfully backfilled location data for {updated_count} visits"
            }
        except Exception as e:
            db.rollback()
            logger.error("Error backfilling visit locations", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to backfill location data: {str(e)}"
            }

    def backfill_session_locations(self, db: Session, batch_size: int = 1000) -> Dict[str, Any]:
        """Backfill missing location data in Sessions from their Visits with batch processing."""
        try:
            # Get total count of sessions needing update (missing or XX location)
            total_to_update = db.query(func.count(VisitSession.id)).filter(
                db.or_(
                    VisitSession.country.is_(None),
                    VisitSession.country == "XX",
                    db.and_(VisitSession.city.is_(None)),
                    db.and_(VisitSession.city == "Unknown")
                )
            ).scalar() or 0

            if total_to_update == 0:
                return {
                    "success": True,
                    "updated_sessions": 0,
                    "message": "No sessions need location backfilling"
                }

            updated_count = 0
            offset = 0

            # Process in batches to avoid memory issues
            while offset < total_to_update:
                # Get a batch of sessions that need updating
                batch = db.query(VisitSession).filter(
                    db.or_(
                        VisitSession.country.is_(None),
                        VisitSession.country == "XX",
                        db.and_(VisitSession.city.is_(None)),
                        db.and_(VisitSession.city == "Unknown")
                    )
                ).offset(offset).limit(batch_size).all()

                if not batch:
                    break

                # For each session, find the best location from its visits
                for session in batch:
                    changed = False

                    # Find visits for this session that have good location data
                    best_visit = db.query(Visit).filter(
                        Visit.session_id == session.id,
                        Visit.country.isnot(None),
                        Visit.country != "XX"
                    ).order_by(Visit.timestamp.desc()).first()

                    if best_visit:
                        # Update session with best visit's location
                        if (not session.country or session.country == "XX") and best_visit.country:
                            session.country = best_visit.country
                            changed = True

                        if (not session.city or session.city == "Unknown") and best_visit.city:
                            session.city = best_visit.city
                            changed = True

                        if changed:
                            db.add(session)
                            updated_count += 1

                # Commit the batch
                db.commit()
                logger.info(f"Backfilled location for {len(batch)} sessions (total: {updated_count}/{total_to_update})")

                offset += batch_size

                # If batch was smaller than batch_size, we're done
                if len(batch) < batch_size:
                    break

            return {
                "success": True,
                "updated_sessions": updated_count,
                "total_processed": total_to_update,
                "message": f"Successfully backfilled location data for {updated_count} sessions"
            }
        except Exception as e:
            db.rollback()
            logger.error("Error backfilling session locations", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to backfill session location data: {str(e)}"
            }

    def get_visitor_categories(
        self,
        db: Session,
        days: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get detailed visitor categorization."""
        if start_date or end_date:
            since = start_date or (datetime.now() - timedelta(days=days))
            until = end_date
        else:
            since = datetime.now() - timedelta(days=days)
            until = None
        
        # Categorize visitors - simplified approach
        chatgpt_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.user_agent.ilike('%gpt%')
        )
        if until:
            chatgpt_query = chatgpt_query.filter(Visit.timestamp <= until)
        chatgpt = chatgpt_query.scalar() or 0
        
        claude_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.user_agent.ilike('%claude%')
        )
        if until:
            claude_query = claude_query.filter(Visit.timestamp <= until)
        claude = claude_query.scalar() or 0
        
        perplexity_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.user_agent.ilike('%perplexity%')
        )
        if until:
            perplexity_query = perplexity_query.filter(Visit.timestamp <= until)
        perplexity = perplexity_query.scalar() or 0
        
        google_ai_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.user_agent.ilike('%google%'),
            Visit.user_agent.ilike('%ai%')
        )
        if until:
            google_ai_query = google_ai_query.filter(Visit.timestamp <= until)
        google_ai = google_ai_query.scalar() or 0
        
        other_ai_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == True,
            ~Visit.user_agent.ilike('%gpt%'),
            ~Visit.user_agent.ilike('%claude%'),
            ~Visit.user_agent.ilike('%perplexity%')
        )
        if until:
            other_ai_query = other_ai_query.filter(Visit.timestamp <= until)
        other_ai = other_ai_query.scalar() or 0
        
        mobile_humans_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == False,
            Visit.user_agent.ilike('%mobile%')
        )
        if until:
            mobile_humans_query = mobile_humans_query.filter(Visit.timestamp <= until)
        mobile_humans = mobile_humans_query.scalar() or 0
        
        desktop_humans_query = db.query(func.count(Visit.id)).filter(
            Visit.timestamp >= since,
            Visit.is_bot == False,
            ~Visit.user_agent.ilike('%mobile%')
        )
        if until:
            desktop_humans_query = desktop_humans_query.filter(Visit.timestamp <= until)
        desktop_humans = desktop_humans_query.scalar() or 0
        
        categories = [
            {'category': 'ChatGPT', 'count': chatgpt},
            {'category': 'Claude', 'count': claude},
            {'category': 'Perplexity', 'count': perplexity},
            {'category': 'Google AI', 'count': google_ai},
            {'category': 'Other AI Crawlers', 'count': other_ai},
            {'category': 'Mobile Humans', 'count': mobile_humans},
            {'category': 'Desktop Humans', 'count': desktop_humans}
        ]
        
        # Filter out zero counts
        categories = [c for c in categories if c['count'] > 0]
        
        return {
            "categories": categories,
            "period_days": days
        }
    
    def get_unified_user_activity(self, db: Session, client_id: str) -> Dict[str, Any]:
        """Get all activity (sessions, visits, events) for a unified user identified by client_id."""
        try:
            # Get all sessions for this client_id
            sessions = db.query(VisitSession).filter(
                VisitSession.client_id == client_id
            ).order_by(VisitSession.first_visit.asc()).all()
            
            # Get all visits for this client_id
            visits = db.query(Visit).filter(
                Visit.client_id == client_id
            ).order_by(Visit.timestamp.asc()).all()
            
            # Get all events for this client_id
            events = db.query(VisitEvent).filter(
                VisitEvent.client_id == client_id
            ).order_by(VisitEvent.timestamp.asc()).all()
            
            # Build a unified timeline
            timeline = []
            
            # Add visits to timeline
            for v in visits:
                timeline.append({
                    "type": "visit",
                    "id": v.id,
                    "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                    "session_id": v.session_id,
                    "page_url": v.page_url,
                    "referrer": v.referrer,
                    "country": v.country,
                    "city": v.city,
                    "is_bot": v.is_bot,
                    "crawler_type": v.crawler_type,
                    "source": v.source,
                    "medium": v.medium,
                    "campaign": v.campaign,
                })
            
            # Add events to timeline
            for e in events:
                timeline.append({
                    "type": "event",
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "session_id": e.session_id,
                    "visit_id": e.visit_id,
                    "event_type": e.event_type,
                    "page_url": e.page_url,
                    "data": e.event_data,
                })
            
            # Sort timeline by timestamp
            timeline.sort(key=lambda x: x.get("timestamp") or "")
            
            # Calculate summary stats
            unique_sessions = len(sessions)
            unique_domains = len(set(v.page_domain for v in visits if v.page_domain))
            first_seen = sessions[0].first_visit if sessions else None
            last_seen = sessions[-1].last_visit if sessions else None
            
            return {
                "client_id": client_id,
                "summary": {
                    "unique_sessions": unique_sessions,
                    "total_visits": len(visits),
                    "total_events": len(events),
                    "unique_domains": unique_domains,
                    "first_seen": first_seen.isoformat() if first_seen else None,
                    "last_seen": last_seen.isoformat() if last_seen else None,
                },
                "sessions": [
                    {
                        "session_id": s.id,
                        "first_visit": s.first_visit.isoformat() if s.first_visit else None,
                        "last_visit": s.last_visit.isoformat() if s.last_visit else None,
                        "visit_count": s.visit_count,
                        "ip_address": s.ip_address,
                        "country": s.country,
                        "city": s.city,
                    }
                    for s in sessions
                ],
                "timeline": timeline,
            }
        except Exception as e:
            logger.error("Error getting unified user activity", error=str(e), client_id=client_id)
            return {
                "client_id": client_id,
                "error": str(e),
                "summary": {},
                "sessions": [],
                "timeline": [],
            }

    def get_journey_timeline(self, db: Session, client_id: str, limit: int = 200, offset: int = 0) -> Dict[str, Any]:
        """Get a unified journey timeline for a client_id with pagination."""
        import json

        try:
            visits_count = db.query(func.count(Visit.id)).filter(Visit.client_id == client_id).scalar() or 0
            events_count = db.query(func.count(VisitEvent.id)).filter(VisitEvent.client_id == client_id).scalar() or 0
            total = visits_count + events_count

            rows = db.execute(
                text(
                    """
                    SELECT
                        'visit' AS item_type,
                        id,
                        timestamp,
                        page_url,
                        referrer,
                        path,
                        page_domain,
                        NULL::text AS referrer_domain,
                        source,
                        medium,
                        campaign,
                        tracking_id,
                        is_bot,
                        crawler_type,
                        NULL::text AS event_type,
                        NULL::json AS event_data
                    FROM visits
                    WHERE client_id = :client_id
                    UNION ALL
                    SELECT
                        'event' AS item_type,
                        id,
                        timestamp,
                        page_url,
                        referrer,
                        path,
                        page_domain,
                        referrer_domain,
                        source,
                        medium,
                        campaign,
                        tracking_id,
                        NULL::boolean AS is_bot,
                        NULL::text AS crawler_type,
                        event_type,
                        event_data
                    FROM visit_events
                    WHERE client_id = :client_id
                    ORDER BY timestamp ASC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {"client_id": client_id, "limit": limit, "offset": offset},
            ).mappings().all()

            timeline = []
            for row in rows:
                event_data = row.get("event_data")
                if isinstance(event_data, str):
                    try:
                        event_data = json.loads(event_data)
                    except Exception:
                        event_data = None
                timeline.append(
                    {
                        "type": row.get("item_type"),
                        "id": row.get("id"),
                        "timestamp": row.get("timestamp").isoformat() if row.get("timestamp") else None,
                        "page_url": row.get("page_url"),
                        "referrer": row.get("referrer"),
                        "path": row.get("path"),
                        "page_domain": row.get("page_domain"),
                        "referrer_domain": row.get("referrer_domain"),
                        "source": row.get("source"),
                        "medium": row.get("medium"),
                        "campaign": row.get("campaign"),
                        "tracking_id": row.get("tracking_id"),
                        "is_bot": row.get("is_bot"),
                        "crawler_type": row.get("crawler_type"),
                        "event_type": row.get("event_type"),
                        "data": event_data,
                    }
                )

            return {
                "client_id": client_id,
                "timeline": timeline,
                "total_count": total,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "current_page": (offset // limit) + 1,
                "total_pages": ((total - 1) // limit) + 1 if total > 0 else 0,
            }
        except Exception as e:
            logger.error("Error getting journey timeline", error=str(e), client_id=client_id)
            return {
                "client_id": client_id,
                "timeline": [],
                "total_count": 0,
                "has_next": False,
                "has_prev": False,
                "current_page": 1,
                "total_pages": 0,
                "error": str(e),
            }

    def list_journey_summaries(
        self,
        db: Session,
        target_path: Optional[str] = None,
        with_captured_only: bool = False,
        with_network_data: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List journey summaries grouped by client_id with optional target path and date range filter."""
        try:
            target_filter = ""
            captured_filter = ""
            network_filter = ""
            date_filter = ""
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            
            # Target path filter - support multiple comma-separated paths
            # Each path must match exactly or as a prefix (e.g., /demo matches /demo and /demo/*)
            if target_path:
                # Split by comma and trim whitespace
                paths = [p.strip() for p in target_path.split(',') if p.strip()]
                
                if len(paths) == 1:
                    # Single path: match exactly or as prefix
                    target_filter = "AND EXISTS (SELECT 1 FROM visits v2 WHERE v2.client_id = j.client_id AND (v2.path = :target_path_0 OR v2.path LIKE :target_path_0_prefix))"
                    params["target_path_0"] = paths[0]
                    params["target_path_0_prefix"] = f"{paths[0]}/%"
                elif len(paths) > 1:
                    # Multiple paths: ALL must be present in the journey
                    conditions = []
                    for i, path in enumerate(paths):
                        conditions.append(f"EXISTS (SELECT 1 FROM visits v2 WHERE v2.client_id = j.client_id AND (v2.path = :target_path_{i} OR v2.path LIKE :target_path_{i}_prefix))")
                        params[f"target_path_{i}"] = path
                        params[f"target_path_{i}_prefix"] = f"{path}/%"
                    target_filter = "AND " + " AND ".join(conditions)
            
            if with_captured_only:
                captured_filter = "AND (up.email IS NOT NULL OR up.name IS NOT NULL)"
            if with_network_data:
                network_filter = "AND cd.captured_data IS NOT NULL AND cd.captured_data <> ''"
            
            # Date range filter
            if start_date and end_date:
                date_filter = "AND DATE(v.timestamp) BETWEEN :start_date AND :end_date"
                params["start_date"] = start_date
                params["end_date"] = end_date
            elif start_date:
                date_filter = "AND DATE(v.timestamp) >= :start_date"
                params["start_date"] = start_date
            elif end_date:
                date_filter = "AND DATE(v.timestamp) <= :end_date"
                params["end_date"] = end_date

            total = db.execute(
                text(
                    f"""
                    WITH base_clients AS (
                        SELECT DISTINCT v.client_id
                        FROM visits v
                        WHERE v.client_id IS NOT NULL AND v.path IS NOT NULL
                        {target_filter.replace("j.client_id", "v.client_id")}
                    ),
                    user_profile AS (
                        SELECT
                            ev.client_id,
                            MAX(CASE WHEN LOWER(ev.field_key) LIKE '%email%' THEN ev.field_value END) AS email,
                            MAX(CASE WHEN LOWER(ev.field_key) LIKE '%name%' THEN ev.field_value END) AS name
                        FROM (
                            SELECT
                                client_id,
                                (event_data::jsonb)->>'field_name' AS field_key,
                                (event_data::jsonb)->>'field_value' AS field_value
                            FROM visit_events
                            WHERE event_type = 'form_input' 
                              AND (event_data::jsonb) ? 'field_name'
                              AND timestamp >= NOW() - INTERVAL '90 days'
                            UNION ALL
                            SELECT
                                ve.client_id,
                                kv.key AS field_key,
                                kv.value AS field_value
                            FROM visit_events ve
                            JOIN LATERAL jsonb_each_text((ve.event_data::jsonb)->'form_values') kv ON TRUE
                            WHERE ve.event_type = 'form_submit' 
                              AND (ve.event_data::jsonb) ? 'form_values'
                              AND ve.timestamp >= NOW() - INTERVAL '90 days'
                        ) ev
                        WHERE ev.client_id IS NOT NULL
                          AND ev.field_key IS NOT NULL
                          AND ev.field_value IS NOT NULL
                          AND ev.field_value <> ''
                        GROUP BY ev.client_id
                    )
                    SELECT COUNT(DISTINCT bc.client_id) FROM base_clients bc
                    LEFT JOIN user_profile up ON up.client_id = bc.client_id
                    LEFT JOIN (
                        SELECT 
                            ve.client_id,
                            STRING_AGG(DISTINCT ve.page_url || ': ' || kv.key || '=' || LEFT(kv.value, 100), ' | ' ORDER BY ve.page_url || ': ' || kv.key || '=' || LEFT(kv.value, 100)) AS captured_data
                        FROM visit_events ve
                        JOIN LATERAL jsonb_each_text((ve.event_data::jsonb)->'form_values') kv ON TRUE
                        WHERE ve.event_type = 'form_submit' 
                          AND (ve.event_data::jsonb) ? 'form_values'
                          AND ve.timestamp >= NOW() - INTERVAL '90 days'
                        GROUP BY ve.client_id
                    ) cd ON cd.client_id = bc.client_id
                    WHERE 1=1
                    {captured_filter}
                    {network_filter}
                    """
                ),
                params,
            ).scalar() or 0

            rows = db.execute(
                text(
                    f"""
                    WITH                     visits_by_user AS (
                        SELECT
                            v.client_id,
                            MIN(v.timestamp) AS first_seen,
                            MAX(v.timestamp) AS last_seen,
                            ARRAY_AGG(v.path ORDER BY v.timestamp) AS path_sequence,
                            (ARRAY_AGG(v.referrer ORDER BY v.timestamp))[1] AS first_referrer
                        FROM visits v
                        WHERE v.client_id IS NOT NULL 
                          AND v.path IS NOT NULL
                          AND v.timestamp >= NOW() - INTERVAL '90 days'
                          {date_filter}
                        GROUP BY v.client_id
                    ),
                    event_values AS (
                        SELECT
                            ev.client_id,
                            LOWER(ev.field_key) AS field_key,
                            ev.field_value,
                            ev.timestamp,
                            ROW_NUMBER() OVER (PARTITION BY ev.client_id, LOWER(ev.field_key) ORDER BY ev.timestamp DESC) AS rn
                        FROM (
                            SELECT
                                client_id,
                                timestamp,
                                (event_data::jsonb)->>'field_name' AS field_key,
                                (event_data::jsonb)->>'field_value' AS field_value
                            FROM visit_events
                            WHERE event_type = 'form_input' 
                              AND (event_data::jsonb) ? 'field_name'
                              AND timestamp >= NOW() - INTERVAL '90 days'
                            UNION ALL
                            SELECT
                                ve.client_id,
                                ve.timestamp,
                                kv.key AS field_key,
                                kv.value AS field_value
                            FROM visit_events ve
                            JOIN LATERAL jsonb_each_text((ve.event_data::jsonb)->'form_values') kv ON TRUE
                            WHERE ve.event_type = 'form_submit' 
                              AND (ve.event_data::jsonb) ? 'form_values'
                              AND ve.timestamp >= NOW() - INTERVAL '90 days'
                        ) ev
                        WHERE ev.client_id IS NOT NULL
                          AND ev.field_key IS NOT NULL
                          AND ev.field_value IS NOT NULL
                          AND ev.field_value <> ''
                    ),
                    latest_values AS (
                        SELECT client_id, field_key, field_value
                        FROM event_values
                        WHERE rn = 1
                    ),
                    user_profile AS (
                        SELECT
                            client_id,
                            MAX(CASE WHEN field_key LIKE '%email%' THEN field_value END) AS email,
                            MAX(CASE WHEN field_key LIKE '%name%' THEN field_value END) AS name
                        FROM latest_values
                        GROUP BY client_id
                    ),
                    captured_data AS (
                        SELECT
                            ev.client_id,
                            STRING_AGG(
                                COALESCE(ev.path, 'unknown') || ': ' || ev.field_key || '=' || ev.field_value,
                                ' | ' ORDER BY ev.timestamp
                            ) AS captured_data
                        FROM (
                            SELECT
                                client_id,
                                timestamp,
                                path,
                                LOWER((event_data::jsonb)->>'field_name') AS field_key,
                                (event_data::jsonb)->>'field_value' AS field_value
                            FROM visit_events
                            WHERE event_type = 'form_input' 
                              AND (event_data::jsonb) ? 'field_name'
                              AND timestamp >= NOW() - INTERVAL '90 days'
                            UNION ALL
                            SELECT
                                ve.client_id,
                                ve.timestamp,
                                ve.path,
                                LOWER(kv.key) AS field_key,
                                kv.value AS field_value
                            FROM visit_events ve
                            JOIN LATERAL jsonb_each_text((ve.event_data::jsonb)->'form_values') kv ON TRUE
                            WHERE ve.event_type = 'form_submit' 
                              AND (ve.event_data::jsonb) ? 'form_values'
                              AND ve.timestamp >= NOW() - INTERVAL '90 days'
                        ) ev
                        WHERE ev.client_id IS NOT NULL
                          AND ev.field_key IS NOT NULL
                          AND ev.field_value IS NOT NULL
                          AND ev.field_value <> ''
                        GROUP BY ev.client_id
                    )
                    SELECT
                        j.client_id,
                        j.first_seen,
                        j.last_seen,
                        j.path_sequence,
                        j.first_referrer,
                        CASE
                            WHEN j.first_referrer IS NULL THEN NULL
                            ELSE REGEXP_REPLACE(j.first_referrer, '^https?://([^/]+).*$','\\1')
                        END AS first_referrer_domain,
                        up.email,
                        up.name,
                        cd.captured_data
                    FROM visits_by_user j
                    LEFT JOIN user_profile up ON up.client_id = j.client_id
                    LEFT JOIN captured_data cd ON cd.client_id = j.client_id
                    WHERE 1=1
                    {target_filter}
                    {captured_filter}
                    {network_filter}
                    ORDER BY j.last_seen DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            ).mappings().all()

            journeys = []
            for row in rows:
                first_seen = row.get("first_seen")
                last_seen = row.get("last_seen")
                duration_seconds = None
                if first_seen and last_seen:
                    duration_seconds = (last_seen - first_seen).total_seconds()
                raw_paths = row.get("path_sequence") or []
                collapsed_paths = []
                for path in raw_paths:
                    if not collapsed_paths or collapsed_paths[-1] != path:
                        collapsed_paths.append(path)
                journeys.append(
                    {
                        "client_id": row.get("client_id"),
                        "email": row.get("email"),
                        "name": row.get("name"),
                        "path_sequence": " → ".join(collapsed_paths) if collapsed_paths else "",
                        "captured_data": row.get("captured_data") or "",
                        "first_referrer": row.get("first_referrer"),
                        "first_referrer_domain": row.get("first_referrer_domain"),
                        "first_seen": first_seen.isoformat() if first_seen else None,
                        "last_seen": last_seen.isoformat() if last_seen else None,
                        "duration_seconds": duration_seconds,
                    }
                )

            return {
                "journeys": journeys,
                "total_count": total,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "current_page": (offset // limit) + 1,
                "total_pages": ((total - 1) // limit) + 1 if total > 0 else 0,
            }
        except Exception as e:
            logger.error("Error listing journey summaries", error=str(e))
            return {
                "journeys": [],
                "total_count": 0,
                "has_next": False,
                "has_prev": False,
                "current_page": 1,
                "total_pages": 0,
                "error": str(e),
            }

    def export_journey_summaries(
        self,
        db: Session,
        target_path: Optional[str] = None,
        with_captured_only: bool = False,
        with_network_data: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000,
    ):
        """Export journey summaries with optional filters as a generator."""
        data = self.list_journey_summaries(
            db,
            target_path=target_path,
            with_captured_only=with_captured_only,
            with_network_data=with_network_data,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=0,
        )
        for row in data.get("journeys", []):
            yield {
                "client_id": row.get("client_id") or "",
                "email": row.get("email") or "",
                "name": row.get("name") or "",
                "path_sequence": row.get("path_sequence") or "",
                "captured_data": row.get("captured_data") or "",
                "first_referrer": row.get("first_referrer") or "",
                "first_referrer_domain": row.get("first_referrer_domain") or "",
                "first_seen": row.get("first_seen") or "",
                "last_seen": row.get("last_seen") or "",
                "duration_seconds": row.get("duration_seconds") or "",
            }

    def get_page_flow_summary(self, db: Session, days: int = 7, limit: int = 100) -> Dict[str, Any]:
        """Summarize page-to-page flows across sessions."""
        since = datetime.now() - timedelta(days=days)
        rows = db.execute(
            text(
                """
                SELECT prev_path, path, COUNT(*) AS count
                FROM (
                    SELECT
                        session_id,
                        path,
                        LAG(path) OVER (PARTITION BY session_id ORDER BY timestamp) AS prev_path
                    FROM visits
                    WHERE timestamp >= :since AND path IS NOT NULL
                ) t
                WHERE prev_path IS NOT NULL AND path IS NOT NULL
                GROUP BY prev_path, path
                ORDER BY count DESC
                LIMIT :limit
                """
            ),
            {"since": since, "limit": limit},
        ).mappings().all()

        flows = [{"from": row["prev_path"], "to": row["path"], "count": row["count"]} for row in rows]
        return {"flows": flows, "period_days": days}
    
    def list_unified_users(self, db: Session, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List unique users by client_id with their activity summary."""
        try:
            # Get distinct client_ids with activity counts
            query = db.query(
                Visit.client_id,
                func.count(func.distinct(Visit.session_id)).label('session_count'),
                func.count(Visit.id).label('visit_count'),
                func.min(Visit.timestamp).label('first_seen'),
                func.max(Visit.timestamp).label('last_seen'),
            ).filter(
                Visit.client_id.isnot(None)
            ).group_by(Visit.client_id).order_by(desc('last_seen'))
            
            # Get total count (cached estimate ideally, but count(distinct) is heavy)
            # For now, keep standard count
            total = db.query(func.count(func.distinct(Visit.client_id))).filter(
                Visit.client_id.isnot(None)
            ).scalar() or 0
            
            # Get paginated results
            users = query.offset(offset).limit(limit).all()
            
            if not users:
                 return {
                    "users": [],
                    "total_count": total,
                    "has_next": False,
                    "has_prev": offset > 0,
                    "current_page": (offset // limit) + 1,
                    "total_pages": ((total - 1) // limit) + 1 if total > 0 else 0
                }

            # --- OPTIMIZATION START: BATCH FETCHING ---
            client_ids = [u.client_id for u in users]
            
            # 1. Batch Get Event Counts
            event_counts_result = db.query(
                VisitEvent.client_id, 
                func.count(VisitEvent.id)
            ).filter(
                VisitEvent.client_id.in_(client_ids)
            ).group_by(VisitEvent.client_id).all()
            
            event_counts_map = {cid: count for cid, count in event_counts_result}
            
            # 2. Batch Get Latest Sessions (Location Info)
            # Use DISTINCT ON (postgres specific) for highest performance
            latest_sessions_result = db.query(
                VisitSession.client_id,
                VisitSession.country,
                VisitSession.city
            ).distinct(VisitSession.client_id).filter(
                VisitSession.client_id.in_(client_ids)
            ).order_by(
                VisitSession.client_id, 
                desc(VisitSession.last_visit)
            ).all()
            
            latest_sessions_map = {
                row.client_id: {'country': row.country, 'city': row.city} 
                for row in latest_sessions_result
            }
            # --- OPTIMIZATION END ---
            
            # Build user list combining the batch data
            user_list = []
            for user in users:
                client_id = user.client_id
                
                # O(1) Lookup from maps
                event_count = event_counts_map.get(client_id, 0)
                session_info = latest_sessions_map.get(client_id, {})
                
                user_list.append({
                    "client_id": client_id,
                    "session_count": user.session_count,
                    "visit_count": user.visit_count,
                    "event_count": event_count,
                    "first_seen": user.first_seen.isoformat() if user.first_seen else None,
                    "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                    "last_country": session_info.get('country'),
                    "last_city": session_info.get('city'),
                })
            
            return {
                "users": user_list,
                "total_count": total,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "current_page": (offset // limit) + 1,
                "total_pages": ((total - 1) // limit) + 1 if total > 0 else 0
            }
        except Exception as e:
            logger.error("Error listing unified users", error=str(e))
            return {
                "users": [],
                "total_count": 0,
                "has_next": False,
                "has_prev": False,
                "current_page": 1,
                "total_pages": 0,
                "error": str(e)
            }