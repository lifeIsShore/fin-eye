"""
Script to migrate existing static markdown blog posts to the database.
"""

import sys
import os
import re
from datetime import datetime

# Add the project root to the python path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.models.blog import BlogPost

FRONTEND_CONTENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'content', 'blog'))

def parse_frontmatter(content: str):
    """Simple frontmatter parser."""
    if not content.startswith('---'):
        return {}, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    meta_raw = parts[1].strip()
    markdown = parts[2].strip()
    
    meta = {}
    for line in meta_raw.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            meta[k] = v
            
    return meta, markdown


def run_migration():
    if not os.path.exists(FRONTEND_CONTENT_DIR):
        print(f"Content directory not found: {FRONTEND_CONTENT_DIR}")
        return

    db = SessionLocal()
    try:
        files = [f for f in os.listdir(FRONTEND_CONTENT_DIR) if f.endswith('.md')]
        print(f"Found {len(files)} markdown posts to migrate.")

        for filename in files:
            slug = filename.replace('.md', '')
            
            # Check if this slug already exists
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                print(f"Post with slug '{slug}' already exists in DB. Skipping.")
                continue
                
            file_path = os.path.join(FRONTEND_CONTENT_DIR, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content_raw = f.read()
                
            meta, markdown = parse_frontmatter(content_raw)
            
            # Publish date parsing if exists
            pub_date = datetime.utcnow()
            if meta.get('date'):
                try:
                    pub_date = datetime.strptime(meta['date'], '%B %d, %Y')
                except Exception:
                    pass
            
            post = BlogPost(
                title=meta.get('title', slug.replace('-', ' ').title()),
                slug=slug,
                summary=meta.get('summary', 'A Fin-Eye blog post.'),
                category=meta.get('category', 'General'),
                read_time=meta.get('readTime', '5 min read'),
                author=meta.get('author', 'Fin-Eye Team'),
                content_md=markdown,
                status="published",
                published_at=pub_date,
                created_at=pub_date,
                updated_at=pub_date
            )
            
            db.add(post)
            print(f"Migrated: '{post.title}' ({post.slug})")
            
        db.commit()
        print("Migration complete!")
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
