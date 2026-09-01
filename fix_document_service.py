import re

with open('backend/app/services/document_service.py', 'r') as f:
    content = f.read()

# Fix get_drive_stats
content = content.replace(
    '.where(Document.tenant_id == tenant_id)',
    '.where(Document.tenant_id == tenant_id, Document.is_trashed == False)'
)

# Fix cleanup_expired_trashed_items
old_logic = """    for d_id, t_id, retention_class, trashed_at, title in candidate_docs:
        class_days = class_periods.get(retention_class)
        if class_days is None:
            protected_documents.append({"title": title, "retention_class": retention_class})
            continue  # permanent class, or an unrecognized one — fail safe, never purge
        if now - trashed_at < timedelta(days=class_days):
            days_remaining = class_days - (now - trashed_at).days
            pending_documents.append({"title": title, "retention_class": retention_class, "days_remaining": max(days_remaining, 0)})
            continue
        actor_id = await _resolve_policy_actor(db, t_id, actor_cache)"""

new_logic = """    for d_id, t_id, retention_class, trashed_at, title in candidate_docs:
        class_days = class_periods.get(retention_class)
        
        if retention_days > 0:
            if class_days is None:
                protected_documents.append({"title": title, "retention_class": retention_class})
                continue  # permanent class, or an unrecognized one — fail safe, never purge
            if now - trashed_at < timedelta(days=class_days):
                days_remaining = class_days - (now - trashed_at).days
                pending_documents.append({"title": title, "retention_class": retention_class, "days_remaining": max(days_remaining, 0)})
                continue
                
        actor_id = await _resolve_policy_actor(db, t_id, actor_cache)"""

content = content.replace(old_logic, new_logic)

with open('backend/app/services/document_service.py', 'w') as f:
    f.write(content)
