import time
import os
import utils
import constants
import rainbow_tables

def _perform_rainbow_table_lookup(algorithm, params, target_hash, stop_event, update_ui_callback, total_lookups):
    start_crack_time = time.time()
    manager = rainbow_tables.get_rainbow_manager()
    
    stats = manager.get_statistics()
    total_hashes_available = stats.get('total_hashes', 0)
    
    update_ui_callback(0, 1, f"Starting {algorithm} rainbow table lookup...\n", True, 0)
    update_ui_callback(0, 1, f"Rainbow table contains {total_hashes_available:,} precomputed hashes\n", True, 0)
    
    bloom_stats = f"Bloom filter efficiency: {stats.get('bloom_hit_ratio', 0):.2%}"
    cache_stats = f"Cache hit ratio: {stats.get('cache_hit_ratio', 0):.2%}"
    update_ui_callback(0, 1, f"{bloom_stats} | {cache_stats}\n", True, 0)
    
    try:
        update_ui_callback(0, 1, f"Searching for hash: {target_hash[:32]}...\n", True, 0)
        
        lookup_key = target_hash
        if algorithm != "bcrypt": 
            lookup_key = target_hash.lower()

        found_password = manager.lookup_hash(lookup_key, algorithm)
        
        elapsed_time = time.time() - start_crack_time
        speed = 1 / max(elapsed_time, 0.001)  
        
        if found_password:
            update_ui_callback(1, 1, "", False, speed)
            update_ui_callback(1, 1, f"Password found in rainbow table: {found_password}\n", True, speed)
            return found_password
        else:
            update_ui_callback(1, 1, f"Hash not found in rainbow table\n", True, speed)
            return None
            
    except Exception as e:
        update_ui_callback(0, 1, f"Error during rainbow table lookup: {str(e)}\n", True, 0)
        return None

def _perform_wordlist_hash_crack(algorithm, params, target_hash, stop_event, update_ui_callback, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    wordlist_path = params["wordlist_path"]
    max_word_len = params.get("max_word_len", 0)
    start_crack_time = time.time()
    log_update_frequency = 1000 
    update_ui_callback(0, total_candidates_to_try, f"Starting {algorithm} wordlist attack from: {os.path.basename(wordlist_path)}\n", True, 0)
    
    update_ui_callback(0, total_candidates_to_try, f"Wordlist Crack: save_to_rainbow is {save_to_rainbow}\n", True, 0) 
    
    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:

            for line in f:
                if stop_event.is_set():
                    update_ui_callback(attempts, total_candidates_to_try, "Cracking stopped by user (wordlist).\n", True, 0)
                    return None
                password = line.strip()
                if not password: continue
                if max_word_len > 0 and len(password) > max_word_len: continue
                attempts += 1
                hashed_password = utils.hash_password(password, algorithm)
                
                if save_to_rainbow and hashed_password: 
                    rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "wordlist_candidate")

                if hashed_password == target_hash.lower(): 
                    if save_to_rainbow: 
                        rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "wordlist_match")
                    speed = attempts / (time.time() - start_crack_time + 1e-6)
                    update_ui_callback(attempts, total_candidates_to_try, "", False, speed)
                    return password
                
                if attempts % log_update_frequency == 0 or attempts == total_candidates_to_try or attempts <= 10:
                    speed = attempts / (time.time() - start_crack_time + 1e-6)
                    update_ui_callback(attempts, total_candidates_to_try, f"Trying: {password[:30]}...\n", False, speed)
    except FileNotFoundError:
        update_ui_callback(0, total_candidates_to_try, f"Error: Wordlist file not found at {wordlist_path}\n", True, 0)
        return None
    except Exception as e:
        update_ui_callback(attempts, total_candidates_to_try, f"An error occurred during {algorithm} wordlist cracking: {str(e)}\n", True, 0)
        return None
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui_callback(attempts, total_candidates_to_try, f"{algorithm} wordlist: Password not found after {attempts} attempts.\n", True, speed)
    return None

def _perform_bruteforce_hash_crack(algorithm, params, target_hash, stop_event, update_ui_callback, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    charset = params["charset"]
    min_len = params["min_len"]
    max_len = params["max_len"]
    start_crack_time = time.time()
    log_update_frequency = 50000  
    
    ui_yield_frequency = 10000  
    last_yield_time = time.time()
    last_ui_update = time.time()
    ui_update_interval = 0.1  
    
    batch_size = 1000
    batch_count = 0
    
    update_ui_callback(0, total_candidates_to_try, f"Starting {algorithm} brute-force attack (len {min_len}-{max_len}, charset size {len(charset)})...\n", True, 0)
    
    try:
        password_generator = utils.generate_bruteforce_passwords(charset, min_len, max_len, stop_event)
        
        for password in password_generator:
            if stop_event.is_set():
                update_ui_callback(attempts, total_candidates_to_try, "Cracking stopped by user (brute-force).\n", True, 0)
                return None
            
            attempts += 1 
            batch_count += 1
            hashed_password = utils.hash_password(password, algorithm)

            if save_to_rainbow and hashed_password: 
                if batch_count % 100 == 0:  
                    rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "bruteforce_candidate")
            
            if hashed_password == target_hash.lower(): 
                if save_to_rainbow: 
                    rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "bruteforce_match")
                speed = attempts / (time.time() - start_crack_time + 1e-6)

                update_ui_callback(attempts, total_candidates_to_try, "", False, speed)
                return password
            
            current_time = time.time()
            if batch_count >= batch_size or (current_time - last_yield_time) > 0.01:  
                time.sleep(0.001)  
                last_yield_time = current_time
                batch_count = 0
                
                if (current_time - last_ui_update) > ui_update_interval:
                    speed = attempts / (time.time() - start_crack_time + 1e-6)
                    update_ui_callback(attempts, total_candidates_to_try, f"Processing... ({attempts:,} attempts)", False, speed)
                    last_ui_update = current_time
            
            if attempts % log_update_frequency == 0 and attempts > 0:
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                update_ui_callback(attempts, total_candidates_to_try, f"Trying: {password[:30]}...\n", False, speed)
                
    except Exception as e:
        update_ui_callback(attempts, total_candidates_to_try, f"An error occurred during {algorithm} brute-force cracking: {str(e)}\n", True, 0)
        return None
    
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui_callback(attempts, total_candidates_to_try, f"{algorithm} brute-force: Password not found after {attempts} attempts.\n", True, speed)
    return None

def _perform_rule_based_hash_crack(algorithm, params, target_hash, stop_event, update_ui_callback, total_base_words, save_to_rainbow):
    base_words_processed = 0
    total_candidates_generated_and_tested = 0
    wordlist_path = params["wordlist_path"]
    rules_config = params["rules"]
    max_cand_len = params.get("max_candidate_len", 0)
    start_crack_time = time.time()
    log_update_frequency_candidates = 10000  
    
    ui_yield_frequency = 500  
    last_yield_time = time.time()
    last_ui_update = time.time()
    ui_update_interval = 0.1
    
    candidate_batch = []
    batch_size = 100
    
    update_ui_callback(0, total_base_words, f"Starting {algorithm} rule-based attack from: {os.path.basename(wordlist_path)}\n", True, 0)
    
    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if stop_event.is_set():
                    update_ui_callback(base_words_processed, total_base_words, "Cracking stopped by user (rule-based).\n", True, 0)
                    return None
                
                base_word = line.strip()
                if not base_word: continue
                base_words_processed += 1
                
                candidates = list(utils.generate_rule_based_candidates(base_word, rules_config, max_cand_len))
                
                for i, candidate in enumerate(candidates):
                    if stop_event.is_set():
                        update_ui_callback(base_words_processed, total_base_words, "Cracking stopped by user (rule-based inner loop).\n", True, 0)
                        return None
                    
                    total_candidates_generated_and_tested += 1
                    hashed_candidate = utils.hash_password(candidate, algorithm)

                    if save_to_rainbow and hashed_candidate: 
                        if total_candidates_generated_and_tested % 50 == 0:
                            rainbow_tables.add_discovered_hash(algorithm, hashed_candidate, candidate, "rule_based_candidate")
                    
                    if hashed_candidate == target_hash.lower(): 
                        if save_to_rainbow: 
                            rainbow_tables.add_discovered_hash(algorithm, hashed_candidate, candidate, "rule_based_match")
                        speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                        update_ui_callback(base_words_processed, total_base_words, "", False, speed)
                        return candidate

                    current_time = time.time()
                    if (i % ui_yield_frequency == 0 and i > 0) or (current_time - last_yield_time) > 0.005:  
                        time.sleep(0.0001)  
                        last_yield_time = current_time
                        
                        if (current_time - last_ui_update) > ui_update_interval:
                            speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                            update_ui_callback(base_words_processed, total_base_words, f"Processing {base_word[:20]}... ({total_candidates_generated_and_tested:,} candidates)", False, speed)
                            last_ui_update = current_time

                    if total_candidates_generated_and_tested % log_update_frequency_candidates == 0:
                        speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                        update_ui_callback(base_words_processed, total_base_words, f"Trying rule candidate: {candidate[:30]}...\n", False, speed)
                
                if base_words_processed % 10 == 0:
                    time.sleep(0.001)
                    if base_words_processed % 100 == 0:
                        speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                        update_ui_callback(base_words_processed, total_base_words, f"Processing base word: {base_word[:30]}...\n", False, speed)
                        
    except FileNotFoundError:
        update_ui_callback(0, total_base_words, f"Error: Wordlist file not found at {wordlist_path} for rule-based attack.\n", True, 0)
        return None
    except Exception as e:
        update_ui_callback(base_words_processed, total_base_words, f"An error occurred during {algorithm} rule-based cracking: {str(e)}\n", True, 0)
        return None
    
    speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
    update_ui_callback(total_base_words, total_base_words, f"{algorithm} rule-based: Password not found after processing {total_base_words} base words ({total_candidates_generated_and_tested} candidates).\n", True, speed)
    return None

def _perform_wordlist_bcrypt_crack(params, target_hash, stop_event, update_ui, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    wordlist_path = params["wordlist_path"]
    max_word_len = params.get("max_word_len", 0)
    start_crack_time = time.time()
    log_update_frequency = 100
    update_ui(0, total_candidates_to_try, f"Starting bcrypt wordlist attack from: {os.path.basename(wordlist_path)}\n", True, 0)
    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if stop_event.is_set():
                    update_ui(attempts, total_candidates_to_try, "Cracking stopped by user (bcrypt wordlist).\n", True, 0)
                    return None
                password = line.strip()
                if not password: continue
                if max_word_len > 0 and len(password) > max_word_len: continue
                attempts += 1
                
                if utils.verify_bcrypt(password, target_hash):
                    if save_to_rainbow: 
                        rainbow_tables.add_discovered_hash("bcrypt", target_hash, password, "wordlist_bcrypt_match")
                    speed = attempts / (time.time() - start_crack_time + 1e-6)
                    update_ui(attempts, total_candidates_to_try, "", False, speed)

                    return password
                if attempts % log_update_frequency == 0 or attempts == total_candidates_to_try or attempts <= 10:
                    speed = attempts / (time.time() - start_crack_time + 1e-6)
                    update_ui(attempts, total_candidates_to_try, f"Trying: {password[:30]}...\n", False, speed)
    except FileNotFoundError:
        update_ui(0, total_candidates_to_try, f"Error: Wordlist file not found at {wordlist_path}\n", True, 0)
        return None
    except Exception as e:
        update_ui(attempts, total_candidates_to_try, f"An error occurred during bcrypt wordlist cracking: {str(e)}\n", True, 0)
        return None
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui(attempts, total_candidates_to_try, f"Bcrypt wordlist: Password not found after {attempts} attempts.\n", True, speed)
    return None

def _perform_bruteforce_bcrypt_crack(params, target_hash, stop_event, update_ui, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    charset = params["charset"]
    min_len = params["min_len"]
    max_len = params["max_len"]
    start_crack_time = time.time()
    log_update_frequency = 100
    update_ui(0, total_candidates_to_try, f"Starting bcrypt brute-force attack (len {min_len}-{max_len}, charset size {len(charset)})...\n", True, 0)
    try:
        for password in utils.generate_bruteforce_passwords(charset, min_len, max_len, stop_event):
            if stop_event.is_set():
                update_ui(attempts, total_candidates_to_try, "Cracking stopped by user (bcrypt brute-force).\n", True, 0)
                return None
            attempts += 1
            
            if utils.verify_bcrypt(password, target_hash):
                if save_to_rainbow: 
                    rainbow_tables.add_discovered_hash("bcrypt", target_hash, password, "bruteforce_bcrypt_match")
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                update_ui(attempts, total_candidates_to_try, "", False, speed)

                return password
            if attempts % log_update_frequency == 0 or attempts == total_candidates_to_try or attempts <= 10:
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                update_ui(attempts, total_candidates_to_try, f"Trying: {password[:30]}...\n", False, speed)
    except Exception as e:
        update_ui(attempts, total_candidates_to_try, f"An error occurred during bcrypt brute-force cracking: {str(e)}\n", True, 0)
        return None
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui(attempts, total_candidates_to_try, f"Bcrypt brute-force: Password not found after {attempts} attempts.\n", True, speed)
    return None

def _perform_probabilistic_hash_crack(algorithm, params, target_hash, stop_event, update_ui_callback, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    model_dir_path = params["model_dir_path"] 
    max_len = params.get("max_len", constants.DEFAULT_PROBABILISTIC_MAX_LEN)
    seed_keyword = params.get("seed_keyword", "")
    start_crack_time = time.time()
    log_update_frequency = constants.PROBABILISTIC_GEN_BATCH_SIZE 

    if not utils.ONNX_HF_AVAILABLE: 
        update_ui_callback(0, total_candidates_to_try, "ONNX Runtime/Transformers not found. Probabilistic cracking unavailable.\n", True, 0)
        return None
    try:
        onnx_session, tokenizer = utils._load_onnx_model_and_tokenizer(model_dir_path) 
        
        start_message = f"Starting {algorithm} probabilistic cracking with ONNX model: {os.path.basename(model_dir_path)}"
        if seed_keyword: start_message += f"\nUsing seed keyword: '{seed_keyword[:30]}{'...' if len(seed_keyword)>30 else ''}'"
        start_message += "\n"
        update_ui_callback(0, total_candidates_to_try, start_message, True, 0)

        candidate_generator = utils._generate_probabilistic_passwords(
            onnx_session, tokenizer, total_candidates_to_try, max_len, stop_event, seed_keyword
        )
        
        if candidate_generator is None: 
            update_ui_callback(0, total_candidates_to_try, f"Failed to initialize probabilistic candidate generator.\nCracking aborted.\n", True, 0)
            return None

        for password in candidate_generator:
            if stop_event.is_set():
                update_ui_callback(attempts, total_candidates_to_try, "Cracking stopped by user (probabilistic).\n", True, 0)
                return None
            if not password: continue 
            attempts += 1
            hashed_password = utils.hash_password(password, algorithm)

            if save_to_rainbow and hashed_password:
                rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "probabilistic_candidate")
            
            if hashed_password == target_hash.lower():
                if save_to_rainbow: 
                    rainbow_tables.add_discovered_hash(algorithm, hashed_password, password, "probabilistic_match")
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                update_ui_callback(attempts, total_candidates_to_try, "", False, speed)
                return password
            
            if attempts % log_update_frequency == 0 or attempts == total_candidates_to_try or attempts <= 10:
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                display_password = password[:30] + "..." if len(password) > 30 else password
                update_ui_callback(attempts, total_candidates_to_try, f"Trying: {display_password}...\n", False, speed)

    except (ImportError, FileNotFoundError, OSError, RuntimeError) as e: 
        update_ui_callback(0, total_candidates_to_try, f"Error with probabilistic model setup/generation: {str(e)}\nCracking aborted.\n", True, 0)
        return None
    except Exception as e:
        update_ui_callback(attempts, total_candidates_to_try, f"An error occurred during {algorithm} probabilistic cracking: {str(e)}\n", True, 0)
        return None
    
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui_callback(attempts, total_candidates_to_try, f"{algorithm} probabilistic: Password not found after {attempts} candidates.\n", True, speed)
    return None

def _perform_probabilistic_bcrypt_crack(params, target_hash, stop_event, update_ui, total_candidates_to_try, save_to_rainbow):
    attempts = 0
    model_dir_path = params["model_dir_path"]
    max_len = params.get("max_len", constants.DEFAULT_PROBABILISTIC_MAX_LEN)
    seed_keyword = params.get("seed_keyword", "")
    start_crack_time = time.time()
    log_update_frequency = max(1, constants.PROBABILISTIC_GEN_BATCH_SIZE // 2)

    if not utils.ONNX_HF_AVAILABLE: 
        update_ui(0, total_candidates_to_try, "ONNX Runtime/Transformers not found. Probabilistic cracking unavailable.\n", True, 0)
        return None
    try:
        onnx_session, tokenizer = utils._load_onnx_model_and_tokenizer(model_dir_path)
        
        start_message = f"Starting bcrypt probabilistic cracking with ONNX model: {os.path.basename(model_dir_path)}"
        if seed_keyword: start_message += f"\nUsing seed keyword: '{seed_keyword[:30]}{'...' if len(seed_keyword)>30 else ''}'"
        start_message += "\n"
        update_ui(0, total_candidates_to_try, start_message, True, 0)

        candidate_generator = utils._generate_probabilistic_passwords(
            onnx_session, tokenizer, total_candidates_to_try, max_len, stop_event, seed_keyword
        )

        if candidate_generator is None:
            update_ui(0, total_candidates_to_try, f"Failed to initialize probabilistic candidate generator.\nCracking aborted.\n", True, 0)
            return None

        for password in candidate_generator:
            if stop_event.is_set():
                update_ui(attempts, total_candidates_to_try, "Cracking stopped by user (probabilistic bcrypt).\n", True, 0)
                return None
            if not password: continue
            attempts += 1
            
            if utils.verify_bcrypt(password, target_hash):
                if save_to_rainbow:
                    rainbow_tables.add_discovered_hash("bcrypt", target_hash, password, "probabilistic_bcrypt_match")
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                update_ui(attempts, total_candidates_to_try, "", False, speed)
                return password
            
            if attempts % log_update_frequency == 0 or attempts == total_candidates_to_try or attempts <= 10:
                speed = attempts / (time.time() - start_crack_time + 1e-6)
                display_password = password[:30] + "..." if len(password) > 30 else password
                update_ui(attempts, total_candidates_to_try, f"Trying: {display_password}...\n", False, speed)
    except (ImportError, FileNotFoundError, OSError, RuntimeError) as e:
        update_ui(0, total_candidates_to_try, f"Error with probabilistic model setup/generation: {str(e)}\nCracking aborted.\n", True, 0)
        return None
    except Exception as e:
        update_ui(attempts, total_candidates_to_try, f"An error occurred during bcrypt probabilistic cracking: {str(e)}\n", True, 0)
        return None
    speed = attempts / (time.time() - start_crack_time + 1e-6)
    update_ui(attempts, total_candidates_to_try, f"Bcrypt probabilistic: Password not found after {attempts} candidates.\n", True, speed)
    return None

def _perform_rule_based_bcrypt_crack(params, target_hash, stop_event, update_ui, total_base_words, save_to_rainbow):
    base_words_processed = 0
    total_candidates_generated_and_tested = 0
    wordlist_path = params["wordlist_path"]
    rules_config = params["rules"]
    max_cand_len = params.get("max_candidate_len", 0)
    start_crack_time = time.time()
    log_update_frequency_candidates = 200 

    update_ui(0, total_base_words, f"Starting bcrypt rule-based attack from: {os.path.basename(wordlist_path)}\n", True, 0)
    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if stop_event.is_set():
                    update_ui(base_words_processed, total_base_words, "Cracking stopped by user (bcrypt rule-based).\n", True, 0)
                    return None
                base_word = line.strip()
                if not base_word: continue
                base_words_processed += 1

                if base_words_processed % 50 == 0 or base_words_processed == total_base_words or base_words_processed <= 10: 
                    speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                    update_ui(base_words_processed, total_base_words, f"Processing base word: {base_word[:30]}...\n", False, speed)

                for candidate in utils.generate_rule_based_candidates(base_word, rules_config, max_cand_len):
                    if stop_event.is_set():
                        update_ui(base_words_processed, total_base_words, "Cracking stopped by user (bcrypt rule-based inner loop).\n", True, 0)
                        return None
                    total_candidates_generated_and_tested += 1

                    if utils.verify_bcrypt(candidate, target_hash):
                        if save_to_rainbow: 
                            rainbow_tables.add_discovered_hash("bcrypt", target_hash, candidate, "rule_based_bcrypt_match")
                        speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                        update_ui(base_words_processed, total_base_words, "", False, speed)
                        return candidate
                    
                    if total_candidates_generated_and_tested % log_update_frequency_candidates == 0:
                        speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
                        update_ui(base_words_processed, total_base_words, f"Trying rule candidate: {candidate[:30]}...\n", False, speed)
    except FileNotFoundError:
        update_ui(0, total_base_words, f"Error: Wordlist file not found at {wordlist_path} for bcrypt rule-based attack.\n", True, 0)
        return None
    except Exception as e:
        update_ui(base_words_processed, total_base_words, f"An error occurred during bcrypt rule-based cracking: {str(e)}\n", True, 0)
        return None

    speed = total_candidates_generated_and_tested / (time.time() - start_crack_time + 1e-6)
    update_ui(total_base_words, total_base_words, f"Bcrypt rule-based: Password not found after processing {total_base_words} base words ({total_candidates_generated_and_tested} candidates).\n", True, speed)
    return None

def _perform_rainbow_table_bcrypt_lookup(params, target_hash, stop_event, update_ui_callback, total_lookups):
    start_crack_time = time.time()
    manager = rainbow_tables.get_rainbow_manager()
    
    stats = manager.get_statistics() 
    total_hashes_available = stats.get('total_hashes', 0) 

    update_ui_callback(0, 1, "Starting bcrypt 'Rainbow Table' lookup...\n", True, 0)
    update_ui_callback(0, 1, f"Checking against {total_hashes_available:,} stored entries (if applicable to bcrypt).\n", True, 0)

    if stop_event.is_set():
        update_ui_callback(0, 1, "Operation stopped by user before lookup.\n", True, 0)
        return None

    try:
        lookup_key = target_hash 
        
        update_ui_callback(0, 1, f"Searching for bcrypt hash: {target_hash[:40]}...\n", True, 0)
        found_password = manager.lookup_hash(lookup_key, "bcrypt") 
        
        elapsed_time = time.time() - start_crack_time
        speed = 1 / (elapsed_time + 1e-9) 

        if found_password:
            update_ui_callback(1, 1, f"Bcrypt: Password found in 'Rainbow Table': {found_password}\n", True, speed)
            return found_password
        else:
            update_ui_callback(1, 1, f"Bcrypt: Hash not found in 'Rainbow Table' after 1 attempt.\n", True, speed)
            return None
            
    except Exception as e:
        update_ui_callback(0, 1, f"Error during bcrypt 'Rainbow Table' lookup: {str(e)}\n", True, 0)
        return None

def crack_password_main(target_hash, selected_hash_type, attack_mode, attack_params, stop_event, update_ui_callback_gui):
    update_ui_callback_gui(0, 1, f"Starting password cracking process (Mode: {attack_mode})...\n", True, 0)
    total_items = 0
    actual_hash_type = selected_hash_type
    save_to_rainbow = attack_params.get("save_to_rainbow", True) 

    update_ui_callback_gui(0, 1, f"Logic Main: save_to_rainbow flag received as: {save_to_rainbow}\n", True, 0)

    if selected_hash_type == "Auto-Detect":
        update_ui_callback_gui(0, 1, "Auto-detecting hash type...\n", True, 0)
        actual_hash_type = utils.detect_hash_type(target_hash, update_ui_callback_gui)
        if actual_hash_type is None:
            update_ui_callback_gui(0, 1, "Failed to auto-detect hash type. Select manually.\nCracking aborted.\n", True, 0)
            return None, selected_hash_type
        update_ui_callback_gui(0, 1, f"Detected hash type: {actual_hash_type}\n", True, 0)

    if attack_mode == "Wordlist":
        if not os.path.exists(attack_params["wordlist_path"]):
            update_ui_callback_gui(0, 1, f"Wordlist file not found: {attack_params['wordlist_path']}\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        total_items = utils.count_wordlist_lines(attack_params["wordlist_path"])
        if total_items == 0:
            update_ui_callback_gui(0, 1, "Wordlist is empty or could not be read.\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        update_ui_callback_gui(0, total_items, f"Wordlist contains {total_items} entries.\n", True, 0)
    elif attack_mode == "Brute-Force":
        charset_size = len(attack_params["charset"]); min_l, max_l = attack_params["min_len"], attack_params["max_len"]
        total_items = utils.calculate_bruteforce_combinations(charset_size, min_l, max_l)
        if total_items == 0 and charset_size > 0 and min_l <= max_l : 
            update_ui_callback_gui(0, 1, "Brute-force: No combinations to test.\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        if total_items > constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS:
            update_ui_callback_gui(0, total_items, f"Brute-force: {total_items-1}+ combinations. Progress bar may be approximate.\n", True, 0)
        else:
            update_ui_callback_gui(0, total_items, f"Brute-force: {total_items} combinations to test.\n", True, 0)
    elif attack_mode == "Rule-Based":
        if not os.path.exists(attack_params["wordlist_path"]):
            update_ui_callback_gui(0, 1, f"Wordlist file not found for Rule-Based attack: {attack_params['wordlist_path']}\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        total_items = utils.count_wordlist_lines(attack_params["wordlist_path"])
        if total_items == 0:
            update_ui_callback_gui(0, 1, "Wordlist for Rule-Based attack is empty or could not be read.\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        update_ui_callback_gui(0, total_items, f"Rule-Based attack: {total_items} base words from wordlist.\n", True, 0)
    elif attack_mode == "Probabilistic":
        if not utils.ONNX_HF_AVAILABLE: 
            update_ui_callback_gui(0, 1, "Probabilistic mode requires ONNX Runtime and Transformers.\nPlease install them and export your model to ONNX.\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        if not os.path.isdir(attack_params["model_dir_path"]):
            update_ui_callback_gui(0, 1, f"Probabilistic model path is not a valid directory: {attack_params['model_dir_path']}\nCracking aborted.\n", True, 0)
            return None, actual_hash_type
        total_items = attack_params["num_candidates"]
        if total_items <= 0: 
            update_ui_callback_gui(0, 1, "Number of candidates for Probabilistic attack must be greater than 0.\nCracking aborted.\n", True, 0)
            return None, actual_hash_type 
        update_ui_callback_gui(0, total_items, f"Probabilistic attack: {total_items} candidates to generate.\n", True, 0)
    elif attack_mode == "Rainbow Table":
        total_items = 1  
        update_ui_callback_gui(0, total_items, f"Rainbow table lookup: instant hash resolution\n", True, 0)
    else:
        update_ui_callback_gui(0, 1, f"Unsupported attack mode: {attack_mode}\nCracking aborted.\n", True, 0)
        return None, actual_hash_type

    found_password = None
    if actual_hash_type == "bcrypt":
        update_ui_callback_gui(0, total_items, "Starting bcrypt cracking...\n", True, 0)
        if attack_mode == "Wordlist":
            found_password = _perform_wordlist_bcrypt_crack(attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Brute-Force":
            found_password = _perform_bruteforce_bcrypt_crack(attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Rule-Based":
            found_password = _perform_rule_based_bcrypt_crack(attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Probabilistic":
            found_password = _perform_probabilistic_bcrypt_crack(attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Rainbow Table":
            found_password = _perform_rainbow_table_bcrypt_lookup(attack_params, target_hash, stop_event, update_ui_callback_gui, total_items)
    elif actual_hash_type in constants.HASH_ALGORITHMS:
        update_ui_callback_gui(0, total_items, f"Starting {actual_hash_type} cracking...\n", True, 0)
        if attack_mode == "Wordlist":
            found_password = _perform_wordlist_hash_crack(actual_hash_type, attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Brute-Force":
            found_password = _perform_bruteforce_hash_crack(actual_hash_type, attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Rule-Based":
            found_password = _perform_rule_based_hash_crack(actual_hash_type, attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Probabilistic":
            found_password = _perform_probabilistic_hash_crack(actual_hash_type, attack_params, target_hash, stop_event, update_ui_callback_gui, total_items, save_to_rainbow)
        elif attack_mode == "Rainbow Table":
            found_password = _perform_rainbow_table_lookup(actual_hash_type, attack_params, target_hash, stop_event, update_ui_callback_gui, total_items)
    else:
        update_ui_callback_gui(0, total_items, f"Unsupported or unknown hash type: {actual_hash_type}\nCracking aborted.\n", True, 0)
        return None, actual_hash_type

    return found_password, actual_hash_type