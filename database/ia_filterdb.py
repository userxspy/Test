import logging
from struct import pack
import re
import base64
from hydrogram.file_id import FileId
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError
from info import USE_CAPTION_FILTER, DATABASE_URL, DATABASE_NAME, MAX_BTN

logger = logging.getLogger(__name__)

# Single Database with 3 Collections
client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]

# Three Collections
primary_collection = db['Primary']
cloud_collection = db['Cloud']
archive_collection = db['Archive']

# Create indexes for all collections
try:
    primary_collection.create_index([("file_name", TEXT)])
    cloud_collection.create_index([("file_name", TEXT)])
    archive_collection.create_index([("file_name", TEXT)])
    logger.info("Successfully created indexes for all collections")
except Exception as e:
    logger.exception(f"Error creating indexes: {e}")


def db_count_documents():
    """Count documents in all collections"""
    primary_count = primary_collection.count_documents({})
    cloud_count = cloud_collection.count_documents({})
    archive_count = archive_collection.count_documents({})
    return {
        'primary': primary_count,
        'cloud': cloud_count,
        'archive': archive_count,
        'total': primary_count + cloud_count + archive_count
    }


async def save_file(media, collection_type='primary'):
    """Save file in specified collection (primary/cloud/archive)"""
    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+", "", str(media.file_name))
    file_caption = re.sub(r"@\w+", "", str(media.caption)) if media.caption else ""
    
    document = {
        '_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': file_caption
    }
    
    # Select collection based on type
    if collection_type.lower() == 'cloud':
        target_collection = cloud_collection
    elif collection_type.lower() == 'archive':
        target_collection = archive_collection
    else:
        target_collection = primary_collection
    
    try:
        target_collection.insert_one(document)
        logger.info(f'Saved to {collection_type} - {file_name}')
        return 'suc'
    except DuplicateKeyError:
        logger.warning(f'Already Saved in {collection_type} - {file_name}')
        return 'dup'


async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None, collection_type='all'):
    """
    Search in collections
    collection_type: 'all', 'primary', 'cloud', 'archive'
    """
    query = str(query).strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query

    if USE_CAPTION_FILTER:
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter = {'file_name': regex}

    results = []
    
    # Search based on collection_type
    if collection_type == 'all':
        # Search in all collections (Primary first)
        cursor = primary_collection.find(filter)
        results.extend([doc for doc in cursor])
        
        cursor2 = cloud_collection.find(filter)
        results.extend([doc for doc in cursor2])
        
        cursor3 = archive_collection.find(filter)
        results.extend([doc for doc in cursor3])
        
    elif collection_type == 'primary':
        cursor = primary_collection.find(filter)
        results = [doc for doc in cursor]
        
    elif collection_type == 'cloud':
        cursor = cloud_collection.find(filter)
        results = [doc for doc in cursor]
        
    elif collection_type == 'archive':
        cursor = archive_collection.find(filter)
        results = [doc for doc in cursor]

    # Language filter if specified
    if lang:
        lang_files = [file for file in results if lang.lower() in file['file_name'].lower()]
        files = lang_files[offset:][:max_results]
        total_results = len(lang_files)
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
        return files, next_offset, total_results

    total_results = len(results)
    files = results[offset:][:max_results]
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''   
    return files, next_offset, total_results


async def delete_files(query, collection_type='all'):
    """Delete files from specified collection(s)"""
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter = {'file_name': regex}
    
    total_deleted = 0
    
    if collection_type == 'all':
        result1 = primary_collection.delete_many(filter)
        result2 = cloud_collection.delete_many(filter)
        result3 = archive_collection.delete_many(filter)
        total_deleted = result1.deleted_count + result2.deleted_count + result3.deleted_count
        
    elif collection_type == 'primary':
        result = primary_collection.delete_many(filter)
        total_deleted = result.deleted_count
        
    elif collection_type == 'cloud':
        result = cloud_collection.delete_many(filter)
        total_deleted = result.deleted_count
        
    elif collection_type == 'archive':
        result = archive_collection.delete_many(filter)
        total_deleted = result.deleted_count
    
    return total_deleted


async def get_file_details(query):
    """Get file details from any collection"""
    # Search in Primary first
    file_details = primary_collection.find_one({'_id': query})
    if file_details:
        return file_details
    
    # Search in Cloud
    file_details = cloud_collection.find_one({'_id': query})
    if file_details:
        return file_details
    
    # Search in Archive
    file_details = archive_collection.find_one({'_id': query})
    return file_details


async def move_files(query, from_collection, to_collection):
    """Move files from one collection to another"""
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter = {'file_name': regex}
    
    # Select source collection
    if from_collection.lower() == 'cloud':
        source = cloud_collection
    elif from_collection.lower() == 'archive':
        source = archive_collection
    else:
        source = primary_collection
    
    # Select destination collection
    if to_collection.lower() == 'cloud':
        destination = cloud_collection
    elif to_collection.lower() == 'archive':
        destination = archive_collection
    else:
        destination = primary_collection
    
    # Find files to move
    files = list(source.find(filter))
    moved_count = 0
    
    for file in files:
        try:
            # Insert in destination
            destination.insert_one(file)
            # Delete from source
            source.delete_one({'_id': file['_id']})
            moved_count += 1
        except DuplicateKeyError:
            # If already exists in destination, just delete from source
            source.delete_one({'_id': file['_id']})
            moved_count += 1
    
    return moved_count


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id
