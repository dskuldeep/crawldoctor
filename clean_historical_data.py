"""
Clean historical data - remove random/garbage characters from captured form data.

This script cleans the event_data JSON in visit_events table where form submissions
contain non-printable or random character data.
"""
import re
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def is_valid_text(value: str) -> bool:
    """Check if text contains valid, recognizable characters."""
    if not value or not isinstance(value, str):
        return True
    
    # Remove control characters
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', value)
    
    if len(cleaned) == 0:
        return False
    
    # Count recognizable characters (letters, numbers, common punctuation)
    recognizable = re.findall(r'[a-zA-Z0-9\s@._\-+(),:;!?\'"<>/\\&%$#]', cleaned)
    recognizable_count = len(recognizable)
    ratio = recognizable_count / len(cleaned) if len(cleaned) > 0 else 0
    
    # If less than 30% recognizable, it's garbage
    if ratio < 0.3:
        return False
    
    # Must have at least some alphanumeric characters
    if not re.search(r'[a-zA-Z0-9]', cleaned):
        return False
    
    return True


def clean_form_values(form_values: dict) -> dict:
    """Clean form_values dict by removing fields with garbage data."""
    if not isinstance(form_values, dict):
        return form_values
    
    cleaned = {}
    for key, value in form_values.items():
        if isinstance(value, str):
            if is_valid_text(value):
                # Also clean the value
                cleaned_value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', value).strip()
                if cleaned_value:
                    cleaned[key] = cleaned_value
        elif isinstance(value, (int, float, bool)):
            cleaned[key] = value
        elif value is None:
            continue
        else:
            # For complex types, keep as is
            cleaned[key] = value
    
    return cleaned


def clean_historical_data(batch_size: int = 1000, dry_run: bool = True):
    """Clean historical event data."""
    session = Session()
    
    try:
        # Get count of events with form submissions
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM visit_events 
            WHERE event_type IN ('form_submit', 'form_input') 
            AND event_data IS NOT NULL
        """))
        total_count = result.scalar()
        print(f"Total form events to process: {total_count}")
        
        cleaned_count = 0
        unchanged_count = 0
        offset = 0
        
        while True:
            # Fetch batch of events
            result = session.execute(text("""
                SELECT id, event_data 
                FROM visit_events 
                WHERE event_type IN ('form_submit', 'form_input') 
                AND event_data IS NOT NULL
                ORDER BY id
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})
            
            rows = result.fetchall()
            if not rows:
                break
            
            for row in rows:
                event_id, event_data = row
                
                if not event_data:
                    unchanged_count += 1
                    continue
                
                try:
                    # Parse event_data
                    data = event_data if isinstance(event_data, dict) else json.loads(event_data)
                    
                    # Check form_values
                    if 'form_values' in data and isinstance(data['form_values'], dict):
                        original_values = data['form_values']
                        cleaned_values = clean_form_values(original_values)
                        
                        if cleaned_values != original_values:
                            # Update the event_data
                            data['form_values'] = cleaned_values
                            
                            if not dry_run:
                                session.execute(text("""
                                    UPDATE visit_events 
                                    SET event_data = :data 
                                    WHERE id = :id
                                """), {"data": json.dumps(data), "id": event_id})
                            
                            cleaned_count += 1
                            if cleaned_count % 100 == 0:
                                print(f"Cleaned {cleaned_count} events...")
                                if not dry_run:
                                    session.commit()
                        else:
                            unchanged_count += 1
                    
                    # Check field_value for form_input events
                    elif 'field_value' in data and isinstance(data['field_value'], str):
                        original_value = data['field_value']
                        
                        if not is_valid_text(original_value):
                            # Remove or null the field_value
                            data['field_value'] = None
                            
                            if not dry_run:
                                session.execute(text("""
                                    UPDATE visit_events 
                                    SET event_data = :data 
                                    WHERE id = :id
                                """), {"data": json.dumps(data), "id": event_id})
                            
                            cleaned_count += 1
                            if cleaned_count % 100 == 0:
                                print(f"Cleaned {cleaned_count} events...")
                                if not dry_run:
                                    session.commit()
                        else:
                            # Clean control characters
                            cleaned_value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', original_value).strip()
                            if cleaned_value != original_value:
                                data['field_value'] = cleaned_value
                                
                                if not dry_run:
                                    session.execute(text("""
                                        UPDATE visit_events 
                                        SET event_data = :data 
                                        WHERE id = :id
                                    """), {"data": json.dumps(data), "id": event_id})
                                
                                cleaned_count += 1
                                if cleaned_count % 100 == 0:
                                    print(f"Cleaned {cleaned_count} events...")
                                    if not dry_run:
                                        session.commit()
                            else:
                                unchanged_count += 1
                    else:
                        unchanged_count += 1
                
                except Exception as e:
                    print(f"Error processing event {event_id}: {e}")
                    unchanged_count += 1
            
            offset += batch_size
            print(f"Processed {offset} / {total_count} events...")
        
        if not dry_run:
            session.commit()
        
        print(f"\n{'DRY RUN - ' if dry_run else ''}COMPLETE:")
        print(f"  Cleaned: {cleaned_count}")
        print(f"  Unchanged: {unchanged_count}")
        print(f"  Total: {cleaned_count + unchanged_count}")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    dry_run = "--apply" not in sys.argv
    
    if dry_run:
        print("Running in DRY RUN mode. Use --apply to actually clean data.")
    else:
        response = input("This will modify the database. Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    clean_historical_data(batch_size=1000, dry_run=dry_run)
