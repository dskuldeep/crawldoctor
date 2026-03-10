"""Check what events are captured for sign-up and bifrost/enterprise paths."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("CHECKING FUNNEL PATHS: /sign-up and /bifrost/enterprise")
print("=" * 80)

# Check what events exist for these paths
query1 = text("""
    SELECT 
        event_type,
        path,
        COUNT(*) as count,
        MAX(timestamp) as latest_event
    FROM visit_events 
    WHERE path IN ('/sign-up', '/bifrost/enterprise')
    GROUP BY event_type, path 
    ORDER BY count DESC;
""")

print("\n1. Events captured on these paths:")
print("-" * 80)
results = session.execute(query1).fetchall()
if results:
    for row in results:
        print(f"  Path: {row.path:30} | Type: {row.event_type:20} | Count: {row.count:5} | Latest: {row.latest_event}")
else:
    print("  ❌ NO EVENTS FOUND for /sign-up or /bifrost/enterprise")

# Check if we have page_view events
query2 = text("""
    SELECT 
        path,
        COUNT(DISTINCT client_id) as unique_visitors,
        COUNT(*) as total_views,
        MAX(timestamp) as latest_view
    FROM visit_events 
    WHERE path IN ('/sign-up', '/bifrost/enterprise')
      AND event_type = 'page_view'
    GROUP BY path;
""")

print("\n2. Page views for these paths:")
print("-" * 80)
results = session.execute(query2).fetchall()
if results:
    for row in results:
        print(f"  Path: {row.path:30} | Unique: {row.unique_visitors:5} | Total: {row.total_views:5} | Latest: {row.latest_view}")
else:
    print("  ❌ NO PAGE VIEWS FOUND")

# Check if we have form_submit events
query3 = text("""
    SELECT 
        path,
        event_type,
        event_data,
        timestamp
    FROM visit_events 
    WHERE path IN ('/sign-up', '/bifrost/enterprise')
      AND event_type = 'form_submit'
    ORDER BY timestamp DESC
    LIMIT 5;
""")

print("\n3. Recent form submissions (last 5):")
print("-" * 80)
results = session.execute(query3).fetchall()
if results:
    for row in results:
        print(f"  Path: {row.path:30} | Time: {row.timestamp}")
        print(f"  Data: {row.event_data}")
        print()
else:
    print("  ❌ NO FORM SUBMISSIONS FOUND")

# Check what paths ARE being tracked
query4 = text("""
    SELECT 
        path,
        COUNT(*) as count
    FROM visit_events 
    WHERE event_type = 'form_submit'
      AND timestamp > NOW() - INTERVAL '7 days'
    GROUP BY path 
    ORDER BY count DESC
    LIMIT 10;
""")

print("\n4. Top form submission paths (last 7 days):")
print("-" * 80)
results = session.execute(query4).fetchall()
if results:
    for row in results:
        print(f"  Path: {row.path:50} | Count: {row.count}")
else:
    print("  ❌ NO FORM SUBMISSIONS IN LAST 7 DAYS")

# Check if paths have slightly different names
query5 = text("""
    SELECT DISTINCT 
        path
    FROM visit_events 
    WHERE (path ILIKE '%sign%up%' OR path ILIKE '%bifrost%enterprise%')
      AND timestamp > NOW() - INTERVAL '30 days'
    ORDER BY path
    LIMIT 20;
""")

print("\n5. Similar paths that might match:")
print("-" * 80)
results = session.execute(query5).fetchall()
if results:
    for row in results:
        print(f"  {row.path}")
else:
    print("  No similar paths found")

session.close()

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print("""
If no events found:
1. These pages might not have the tracker installed
2. Forms might be submitting via API (not captured after network removal)
3. Path names might be slightly different (check similar paths above)

If page_view but no form_submit:
1. Forms might not be using HTML <form> tags
2. Forms might be in iframes
3. Forms might be submitting via JavaScript fetch/XHR (not captured anymore)

Next steps:
- Visit these pages in your browser
- Open Live Data page
- Submit the forms
- Check if events appear
""")
