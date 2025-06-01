import sqlite3
import threading
import time
import os
import zlib
import hashlib
import json
from collections import deque
import struct
import constants
import utils

class BloomFilter:
    
    def __init__(self, size=constants.RAINBOW_TABLE_BLOOM_FILTER_SIZE, hash_count=constants.RAINBOW_TABLE_BLOOM_HASH_COUNT):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = bytearray(size // 8 + 1)
        self.item_count = 0
    
    def _hash(self, item, seed):
        h = hashlib.sha256(f"{item}{seed}".encode()).hexdigest()
        return int(h[:8], 16) % self.size
    
    def add(self, item):
        for i in range(self.hash_count):
            bit_pos = self._hash(item, i)
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            self.bit_array[byte_pos] |= (1 << bit_offset)
        self.item_count += 1
    
    def __contains__(self, item):
        for i in range(self.hash_count):
            bit_pos = self._hash(item, i)
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            if not (self.bit_array[byte_pos] & (1 << bit_offset)):
                return False
        return True
    
    def save(self, filepath):
        with open(filepath, 'wb') as f:
            f.write(struct.pack('I', self.size))
            f.write(struct.pack('I', self.hash_count))
            f.write(struct.pack('I', self.item_count))
            f.write(self.bit_array)
    
    def load(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.size = struct.unpack('I', f.read(4))[0]
                self.hash_count = struct.unpack('I', f.read(4))[0]
                self.item_count = struct.unpack('I', f.read(4))[0]
                self.bit_array = bytearray(f.read())

class RainbowTableManager:
    
    def __init__(self, db_path=constants.RAINBOW_TABLE_DB_PATH):
        self.db_path = db_path
        self.cache = {}  
        self.cache_order = deque()  
        self.cache_lock = threading.RLock()
        self.db_lock = threading.RLock()
        self.bloom_filter = BloomFilter()
        self.stats = {
            'total_hashes': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bloom_filter_hits': 0,
            'bloom_filter_misses': 0,
            'db_queries': 0,
            'successful_lookups': 0
        }
        self.pending_inserts = deque()
        self.batch_insert_timer = None
        self.initialize_database()
        self.load_bloom_filter()
        self.preload_statistics()
    
    def initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rainbow_hashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algorithm TEXT NOT NULL,
                    hash_value TEXT NOT NULL,
                    password TEXT NOT NULL,
                    password_length INTEGER NOT NULL,
                    charset_type TEXT,
                    date_added INTEGER DEFAULT (strftime('%s', 'now')),
                    source TEXT DEFAULT 'manual',
                    compressed_data BLOB
                )
            """)
            
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_hash_algo ON rainbow_hashes(hash_value, algorithm)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_algorithm ON rainbow_hashes(algorithm)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_password_length ON rainbow_hashes(password_length)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON rainbow_hashes(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date_added ON rainbow_hashes(date_added)")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rainbow_stats (
                    algorithm TEXT PRIMARY KEY,
                    hash_count INTEGER DEFAULT 0,
                    last_updated INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rainbow_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    last_updated INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.commit()
    
    def load_bloom_filter(self):
        bloom_path = self.db_path.replace('.db', '_bloom.dat')
        if os.path.exists(bloom_path):
            try:
                self.bloom_filter.load(bloom_path)
                print(f"Loaded bloom filter with {self.bloom_filter.item_count} items")
            except Exception as e:
                print(f"Failed to load bloom filter: {e}")
                self.rebuild_bloom_filter()
        else:
            self.rebuild_bloom_filter()
    
    def save_bloom_filter(self):
        bloom_path = self.db_path.replace('.db', '_bloom.dat')
        try:
            self.bloom_filter.save(bloom_path)
        except Exception as e:
            print(f"Failed to save bloom filter: {e}")
    
    def rebuild_bloom_filter(self):
        print("Rebuilding bloom filter from database...")
        self.bloom_filter = BloomFilter()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT hash_value FROM rainbow_hashes")
            batch_count = 0
            for row in cursor:
                self.bloom_filter.add(row[0])
                batch_count += 1
                if batch_count % 10000 == 0:
                    print(f"Processed {batch_count} hashes for bloom filter...")
        
        self.save_bloom_filter()
        print(f"Bloom filter rebuilt with {self.bloom_filter.item_count} items")
    
    def preload_statistics(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM rainbow_hashes")
            self.stats['total_hashes'] = cursor.fetchone()[0]
    
    def _manage_cache(self, key, value=None):
        with self.cache_lock:
            if value is not None:  
                if key in self.cache:
                    self.cache_order.remove(key)
                elif len(self.cache) >= constants.RAINBOW_TABLE_CACHE_SIZE:
                    oldest_key = self.cache_order.popleft()
                    del self.cache[oldest_key]
                
                self.cache[key] = value
                self.cache_order.append(key)
                return value
            else:  
                if key in self.cache:
                    self.cache_order.remove(key)
                    self.cache_order.append(key)
                    self.stats['cache_hits'] += 1
                    return self.cache[key]
                else:
                    self.stats['cache_misses'] += 1
                    return None
    
    def lookup_hash(self, target_hash, algorithm):
        
        cache_key = f"{algorithm}:{target_hash}"
        cached_result = self._manage_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        if target_hash not in self.bloom_filter:
            self.stats['bloom_filter_misses'] += 1
            return None
        
        self.stats['bloom_filter_hits'] += 1
        
        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT password, compressed_data FROM rainbow_hashes WHERE hash_value = ? AND algorithm = ? LIMIT 1",
                        (target_hash, algorithm)
                    )
                    row = cursor.fetchone()
                    self.stats['db_queries'] += 1
                    
                    if row:
                        if row['compressed_data']:
                            try:
                                password = zlib.decompress(row['compressed_data']).decode('utf-8')
                            except:
                                password = row['password']
                        else:
                            password = row['password']
                        
                        self._manage_cache(cache_key, password)
                        self.stats['successful_lookups'] += 1
                        return password
                    
                    return None
                    
            except Exception as e:
                print(f"Database lookup error: {e}")
                return None
    
    def add_hash_batch(self, hash_entries, source="manual"):
        if not hash_entries:
            return
        
        compressed_entries = []
        for algorithm, hash_value, password in hash_entries:
            compressed_data = None
            if len(password) > 20:
                try:
                    compressed_data = zlib.compress(password.encode('utf-8'), constants.RAINBOW_TABLE_COMPRESSION_LEVEL)
                    if len(compressed_data) >= len(password.encode('utf-8')):
                        compressed_data = None
                except:
                    compressed_data = None
            
            charset_type = self._detect_charset_type(password)
            
            compressed_entries.append((
                algorithm, hash_value, password, len(password), 
                charset_type, int(time.time()), source, compressed_data
            ))
            
            self.bloom_filter.add(hash_value)
        
        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.executemany("""
                        INSERT OR IGNORE INTO rainbow_hashes 
                        (algorithm, hash_value, password, password_length, charset_type, date_added, source, compressed_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, compressed_entries)
                    
                    inserted_count = conn.total_changes
                    conn.commit()
                    
                    self.stats['total_hashes'] += inserted_count
                    
                    for algorithm, _, _, _, _, _, _, _ in compressed_entries:
                        conn.execute("""
                            INSERT OR REPLACE INTO rainbow_stats (algorithm, hash_count, last_updated)
                            VALUES (?, 
                                    COALESCE((SELECT hash_count FROM rainbow_stats WHERE algorithm = ?), 0) + 1,
                                    ?)
                        """, (algorithm, algorithm, int(time.time())))
                    
                    conn.commit()
                    return inserted_count
                    
            except Exception as e:
                print(f"Batch insert error: {e}")
                return 0
    
    def add_hash_async(self, algorithm, hash_value, password, source="manual"):
        self.pending_inserts.append((algorithm, hash_value, password))
        
        if self.batch_insert_timer is None:
            self.batch_insert_timer = threading.Timer(5.0, self._process_pending_inserts)
            self.batch_insert_timer.start()
        
        if len(self.pending_inserts) >= constants.RAINBOW_TABLE_BATCH_SIZE:
            self._process_pending_inserts()
    
    def _process_pending_inserts(self):
        if self.batch_insert_timer:
            self.batch_insert_timer.cancel()
            self.batch_insert_timer = None
        
        if self.pending_inserts:
            batch = list(self.pending_inserts)
            self.pending_inserts.clear()
            self.add_hash_batch(batch, source="async_batch")
            print(f"Added batch of {len(batch)} hashes to rainbow table")
    
    def _detect_charset_type(self, password):
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if has_lower and has_upper and has_digit and has_special:
            return "mixed_all"
        elif has_lower and has_upper and has_digit:
            return "mixed_alphanumeric"
        elif has_lower and has_digit:
            return "lower_digit"
        elif has_upper and has_digit:
            return "upper_digit"
        elif has_lower and has_upper:
            return "mixed_alpha"
        elif has_digit:
            return "numeric"
        elif has_lower:
            return "lowercase"
        elif has_upper:
            return "uppercase"
        else:
            return "special"
    
    def get_statistics(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    algorithm,
                    COUNT(*) as count,
                    AVG(password_length) as avg_length,
                    MIN(password_length) as min_length,
                    MAX(password_length) as max_length
                FROM rainbow_hashes 
                GROUP BY algorithm
            """)
            
            algo_stats = {}
            for row in cursor:
                algo_stats[row[0]] = {
                    'count': row[1],
                    'avg_length': round(row[2], 2),
                    'min_length': row[3],
                    'max_length': row[4]
                }
            
            cursor = conn.execute("""
                SELECT charset_type, COUNT(*) 
                FROM rainbow_hashes 
                GROUP BY charset_type
            """)
            charset_dist = dict(cursor.fetchall())
            
            self.stats.update({
                'algorithm_stats': algo_stats,
                'charset_distribution': charset_dist,
                'cache_hit_ratio': self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses']),
                'bloom_hit_ratio': self.stats['bloom_filter_hits'] / max(1, self.stats['bloom_filter_hits'] + self.stats['bloom_filter_misses'])
            })
            
            return self.stats
    
    def import_wordlist_as_rainbow_table(self, wordlist_path, algorithms, progress_callback=None):
        if not os.path.exists(wordlist_path):
            return False
        
        start_time = time.time()
        total_lines = utils.count_wordlist_lines(wordlist_path)
        processed = 0
        batch = []
        
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                password = line.strip()
                if not password:
                    continue
                
                for algorithm in algorithms:
                    if algorithm == "bcrypt":
                        continue
                    elif algorithm in constants.HASH_ALGORITHMS:
                        hash_value = utils.hash_password(password, algorithm) 
                        if hash_value:
                            batch.append((algorithm, hash_value, password))
                
                processed += 1
                
                if len(batch) >= constants.RAINBOW_TABLE_BATCH_SIZE:
                    self.add_hash_batch(batch, source=f"wordlist:{os.path.basename(wordlist_path)}")
                    batch = []
                
                if progress_callback and processed % 1000 == 0:
                    progress_callback(processed, total_lines, f"Processing: {password[:30]}...", False, processed/max(1, time.time()-start_time))
        
        if batch:
            self.add_hash_batch(batch, source=f"wordlist:{os.path.basename(wordlist_path)}")
        
        return True
    
    def export_rainbow_table(self, output_path, algorithm=None, format='json'):
        query = "SELECT algorithm, hash_value, password FROM rainbow_hashes"
        params = []
        
        if algorithm:
            query += " WHERE algorithm = ?"
            params.append(algorithm)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            
            if format == 'json':
                data = []
                for row in cursor:
                    data.append({
                        'algorithm': row[0],
                        'hash': row[1],
                        'password': row[2]
                    })
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format == 'csv':
                import csv
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Algorithm', 'Hash', 'Password'])
                    writer.writerows(cursor)
        
        return True
    
    def optimize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.execute("REINDEX")
        
        self.rebuild_bloom_filter()
        print("Database optimization completed")
    
    def cleanup(self):
        if self.batch_insert_timer:
            self.batch_insert_timer.cancel()
        
        self._process_pending_inserts()
        
        self.save_bloom_filter()

_rainbow_manager = None
_rainbow_lock = threading.Lock()

def get_rainbow_manager():
    global _rainbow_manager
    with _rainbow_lock:
        if _rainbow_manager is None:
            _rainbow_manager = RainbowTableManager()
        return _rainbow_manager

def add_discovered_hash(algorithm, hash_value, password, source="discovery"):
    manager = get_rainbow_manager()
    manager.add_hash_async(algorithm, hash_value, password, source)
