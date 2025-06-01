import hashlib
import subprocess
import os
import base64
import zlib
import sys 
import itertools
import time
import bcrypt
import constants
import platform 

CITYHASH_AVAILABLE = False
try:
    import cityhash
    CITYHASH_AVAILABLE = True
except ImportError:
    print("cityhash library not found. CityHash algorithms will not be available. Install with: pip install cityhash")

MMH3_AVAILABLE = False
try:
    import mmh3
    MMH3_AVAILABLE = True
except ImportError:
    print("mmh3 library not found. MurmurHash algorithms will not be available. Install with: pip install mmh3")

PYCRYPTODOME_AVAILABLE = False
AES_FIXED_KEY_FOR_HASHING = None
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad as pkcs7_pad
    PYCRYPTODOME_AVAILABLE = True
    AES_FIXED_KEY_FOR_HASHING = hashlib.sha256(b"PolycryptFixedAESKeyForHashing").digest()[:16] 
except ImportError:
    print("pycryptodome library not found. AES-emulated hash will not be available. Install with: pip install pycryptodome")

XXHASH_AVAILABLE = False
try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    print("xxhash library not found. XXHash algorithms will not be available. Install with: pip install xxhash")

ONNX_HF_AVAILABLE = False
_loaded_onnx_session_cache = {}
_loaded_hf_tokenizer_cache = {} 

try:
    from transformers import AutoTokenizer 
    import onnxruntime
    import numpy as np 
    ONNX_HF_AVAILABLE = True 
    print("ONNX Runtime and Hugging Face Tokenizers found. Transformer-based probabilistic generation will use ONNX.")
except ImportError as e:
    print(f"ONNX Runtime or Hugging Face Tokenizers (for tokenizer) or NumPy not found: {e}")
    print("Please install them: pip install onnxruntime transformers numpy")
    print("Transformer-based probabilistic generation will NOT be available.")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def hash_password(password: str, algorithm_name: str):
    password_bytes = password.encode('utf-8', errors='ignore')
    constructor = constants.HASH_ALGORITHMS.get(algorithm_name)

    try:
        if constructor is constants.CUSTOM_HANDLER_SENTINEL:
            if algorithm_name == "CRC32 (HEX)":
                return hex(zlib.crc32(password_bytes) & 0xffffffff)[2:].zfill(8)
            elif algorithm_name == "Murmur3_32":
                if MMH3_AVAILABLE:
                    return hex(mmh3.hash(password_bytes, seed=0) & 0xffffffff)[2:].zfill(8)
                else: print(f"mmh3 library not available for {algorithm_name}"); return None
            elif algorithm_name == "Murmur3_128":
                if MMH3_AVAILABLE:
                    val = mmh3.hash128(password_bytes, seed=0)
                    return val.to_bytes(16, 'big').hex()
                else: print(f"mmh3 library not available for {algorithm_name}"); return None
            elif algorithm_name == "CityHash64":
                if CITYHASH_AVAILABLE:
                    val = cityhash.CityHash64(password_bytes) 
                    return val.to_bytes(8, 'big', signed=False).hex()
                else: print(f"cityhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "CityHash128":
                if CITYHASH_AVAILABLE:
                    val = cityhash.CityHash128(password_bytes) 
                    return val.to_bytes(16, 'big', signed=False).hex()
                else: print(f"cityhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "XXH32":
                if XXHASH_AVAILABLE:
                    return xxhash.xxh32(password_bytes, seed=0).hexdigest()
                else: print(f"xxhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "XXH64":
                if XXHASH_AVAILABLE:
                    return xxhash.xxh64(password_bytes, seed=0).hexdigest()
                else: print(f"xxhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "XXH3_64":
                if XXHASH_AVAILABLE:
                    return xxhash.xxh3_64(password_bytes, seed=0).hexdigest()
                else: print(f"xxhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "XXH3_128":
                if XXHASH_AVAILABLE:
                    return xxhash.xxh3_128(password_bytes, seed=0).hexdigest()
                else: print(f"xxhash library not available for {algorithm_name}"); return None
            elif algorithm_name == "AES-EMU-SHA256":
                if PYCRYPTODOME_AVAILABLE and AES_FIXED_KEY_FOR_HASHING:
                    cipher = AES.new(AES_FIXED_KEY_FOR_HASHING, AES.MODE_ECB)
                    padded_password = pkcs7_pad(password_bytes, AES.block_size)
                    ciphertext = cipher.encrypt(padded_password)
                    return hashlib.sha256(ciphertext).hexdigest()
                else: print(f"pycryptodome library not available for {algorithm_name}"); return None
            else:
                print(f"DEBUG: Unknown custom algorithm_name '{algorithm_name}' in hash_password utility.")
                return None

        elif constructor is hashlib.new: 
            algo_lower = algorithm_name.lower()
            if algo_lower == 'whirlpool' and 'whirlpool' not in hashlib.algorithms_available:
                print(f"Whirlpool not available in this Python's hashlib. OpenSSL version might be too old or not compiled with Whirlpool.")
                return None
            hasher = hashlib.new(algo_lower)
            hasher.update(password_bytes)
            return hasher.hexdigest()

        elif callable(constructor): 
            hasher = constructor()
            hasher.update(password_bytes)
            if algorithm_name == "SHAKE128-256":
                return hasher.hexdigest(32)  
            elif algorithm_name == "SHAKE256-512":
                return hasher.hexdigest(64)  
            else:
                return hasher.hexdigest()
        else:
            print(f"DEBUG: Algorithm '{algorithm_name}' not found or misconfigured in HASH_ALGORITHMS.")
            return None

    except Exception as e:
        print(f"DEBUG: Error during hashing for {algorithm_name} in hash_password utility: {str(e)}")
        return None

def detect_hash_type(target_hash, update_ui_callback):
    if target_hash.startswith(("$2a$", "$2b$", "$2y$")):
        update_ui_callback(0, 1, "Detected hash type: bcrypt (by prefix)\n", True, 0)
        return "bcrypt"
    try:
        update_ui_callback(0, 1, "Attempting hash detection with hashid...\n", True, 0)
        process = subprocess.Popen(["hashid", target_hash], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        output, errors = process.communicate(timeout=5)
        
        if process.returncode != 0 and errors:
             update_ui_callback(0, 1, f"hashid execution error: {errors.strip()}\n", True, 0)

        hashid_suggestions_raw = [] 
        if output: 
            lines = output.strip().split("\n")
            for line in lines:
                if "[+]" in line:
                    suggestion = line.split("[+]")[1].strip()
                    if suggestion: 
                        hashid_suggestions_raw.append(suggestion)

        if not hashid_suggestions_raw:
            update_ui_callback(0, 1, "hashid provided no positive identifications.\n", True, 0)
        else:
            for known_key_original in constants.HASH_ALGORITHMS.keys():
                normalized_known_key = known_key_original.upper().replace("-", "") 
                
                for raw_suggestion in hashid_suggestions_raw:
                    normalized_hashid_suggestion = raw_suggestion.upper().replace("-", "")
                    
                    if normalized_hashid_suggestion == normalized_known_key:
                        update_ui_callback(0, 1, f"Detected hash type via hashid ({raw_suggestion} -> {known_key_original})\n", True, 0)
                        return known_key_original
                    
                    if normalized_hashid_suggestion.startswith(normalized_known_key) and len(normalized_known_key) >= 3: 
                        remainder = normalized_hashid_suggestion[len(normalized_known_key):]
                        if not remainder or remainder.isdigit():
                            update_ui_callback(0, 1, f"Detected hash type via hashid ({raw_suggestion} -> {known_key_original})\n", True, 0)
                            return known_key_original
            
            update_ui_callback(0, 1, f"hashid suggested types ({', '.join(hashid_suggestions_raw)}), but none matched our known list with priority.\n", True, 0)

    except FileNotFoundError:
        update_ui_callback(0, 1, "hashid tool not found. Skipping hashid detection.\n", True, 0)
    except subprocess.TimeoutExpired:
        update_ui_callback(0, 1, "hashid tool timed out. Skipping hashid detection.\n", True, 0)
    except subprocess.CalledProcessError as e:
        update_ui_callback(0, 1, f"hashid execution error: {e.output.strip() if e.output else str(e)}\n", True, 0)
    except Exception as e:
        update_ui_callback(0, 1, f"Error during hashid detection: {str(e)}\n", True, 0)

    update_ui_callback(0, 1, "Attempting hash detection by length...\n", True, 0)
    for algorithm, hash_function_constructor in constants.HASH_ALGORITHMS.items(): 
        try:
            example_hashed_empty = hash_password("", algorithm)
            if example_hashed_empty and len(target_hash) == len(example_hashed_empty):
                update_ui_callback(0, 1, f"Potentially detected hash type by length: {algorithm}\n", True, 0)
                return algorithm
        except Exception: 
            continue
    update_ui_callback(0, 1, "Could not automatically detect hash type.\n", True, 0)
    return None

def verify_bcrypt(password: str, target_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'),
                              target_hash.encode('utf-8'))
    except Exception as e:
        print(f"DEBUG: bcrypt.verify error: {e}")
        return False

def count_wordlist_lines(wordlist_path):
    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def generate_bruteforce_passwords(charset, min_len, max_len, stop_event_ref):
    for length in range(min_len, max_len + 1):
        if stop_event_ref.is_set(): return
        for p_tuple in itertools.product(charset, repeat=length):
            if stop_event_ref.is_set(): return
            yield "".join(p_tuple)

def calculate_bruteforce_combinations(charset_size, min_len, max_len):
    if charset_size == 0: return 0
    total_combinations = 0
    for length in range(min_len, max_len + 1):
        try:
            combinations_for_length = charset_size ** length
            if total_combinations + combinations_for_length > constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS :
                return constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS + 1
            total_combinations += combinations_for_length
        except OverflowError:
             return constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS + 1
    return total_combinations

def generate_rule_based_candidates(base_word, rules_config, max_len):
    candidates = set()
    if not base_word:
        return []
    words_to_process = {base_word}
    if rules_config.get("prepend_append_common"):
        temp_pre_app_words = set()
        for prefix in constants.COMMON_PREFIXES:
            for suffix in constants.COMMON_SUFFIXES:
                if not prefix and not suffix: continue
                candidate = prefix + base_word + suffix
                if max_len == 0 or len(candidate) <= max_len:
                    temp_pre_app_words.add(candidate)
        words_to_process.update(temp_pre_app_words)
    for word in list(words_to_process):
        if max_len == 0 or len(word) <= max_len:
            candidates.add(word)
    transformed_words_stage1 = set(words_to_process)
    if rules_config.get("capitalize_first"):
        for word in list(words_to_process):
            cap_word = word.capitalize()
            if cap_word != word and (max_len == 0 or len(cap_word) <= max_len):
                candidates.add(cap_word)
                transformed_words_stage1.add(cap_word)
    if rules_config.get("reverse_word"):
        for word in list(words_to_process):
            rev_word = word[::-1]
            if rev_word != word and (max_len == 0 or len(rev_word) <= max_len):
                candidates.add(rev_word)
                transformed_words_stage1.add(rev_word)
                if rules_config.get("capitalize_first"):
                    cap_rev_word = rev_word.capitalize()
                    if cap_rev_word != rev_word and (max_len == 0 or len(cap_rev_word) <= max_len):
                        candidates.add(cap_rev_word)
                        transformed_words_stage1.add(cap_rev_word)
    if rules_config.get("toggle_case"):
        for word in list(words_to_process):
            toggled_word = "".join([char.lower() if char.isupper() else char.upper() for char in word])
            if toggled_word != word and (max_len == 0 or len(toggled_word) <= max_len):
                candidates.add(toggled_word)
                transformed_words_stage1.add(toggled_word)
    words_for_num_append = set(candidates)
    if rules_config.get("append_numbers"):
        for word_to_modify in words_for_num_append:
            for num_suffix in constants.NUMBERS_TO_APPEND:
                candidate = word_to_modify + num_suffix
                if max_len == 0 or len(candidate) <= max_len:
                    candidates.add(candidate)
    words_for_leet = set(candidates)
    if rules_config.get("leet_speak"):
        for word_to_leet in words_for_leet:
            if not word_to_leet: continue
            leet_word_chars = []
            changed = False
            for char_original in word_to_leet:
                leet_char = constants.LEET_MAP_SIMPLE.get(char_original, char_original)
                leet_word_chars.append(leet_char)
                if leet_char != char_original:
                    changed = True
            if changed:
                leet_candidate = "".join(leet_word_chars)
                if (max_len == 0 or len(leet_candidate) <= max_len):
                    candidates.add(leet_candidate)
    if max_len > 0:
        return [c for c in candidates if len(c) <= max_len and c]
    return [c for c in list(candidates) if c]

def _load_onnx_model_and_tokenizer(model_dir_path, onnx_model_filename="model.onnx"):
    global _loaded_onnx_session_cache, _loaded_hf_tokenizer_cache 
    if not ONNX_HF_AVAILABLE:
        raise ImportError("ONNX Runtime or Transformers (for tokenizer) not available.")

    tokenizer_path = model_dir_path 
    onnx_model_full_path = os.path.join(model_dir_path, onnx_model_filename)

    if tokenizer_path in _loaded_hf_tokenizer_cache:
        tokenizer = _loaded_hf_tokenizer_cache[tokenizer_path]
        print(f"Using cached HF tokenizer from {tokenizer_path}")
    else:
        print(f"Loading HF tokenizer from {tokenizer_path}...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            _loaded_hf_tokenizer_cache[tokenizer_path] = tokenizer
        except Exception as e:
            print(f"Error loading tokenizer from {tokenizer_path}: {e}")
            raise

    if onnx_model_full_path in _loaded_onnx_session_cache:
        onnx_session = _loaded_onnx_session_cache[onnx_model_full_path]
        print(f"Using cached ONNX session from {onnx_model_full_path}")
    else:
        print(f"Loading ONNX model from {onnx_model_full_path}...")
        if not os.path.exists(onnx_model_full_path):
            raise FileNotFoundError(f"ONNX model file not found at {onnx_model_full_path}. Please ensure it was exported correctly.")
        try:
            providers = ['CPUExecutionProvider']
            if onnxruntime.get_device() == 'GPU':
                available_providers = onnxruntime.get_available_providers()
                if 'CUDAExecutionProvider' in available_providers:
                    print("Attempting to use CUDAExecutionProvider for ONNX.")
                    providers.insert(0, 'CUDAExecutionProvider')
                elif 'DmlExecutionProvider' in available_providers and platform.system() == "Windows":
                    print("Attempting to use DmlExecutionProvider for ONNX (DirectML).")
                    providers.insert(0, 'DmlExecutionProvider')
                else:
                    print("CUDA/DML Execution Provider not found or ONNX Runtime not built with GPU support. Using CPU for ONNX.")
            
            onnx_session = onnxruntime.InferenceSession(onnx_model_full_path, providers=providers)
            _loaded_onnx_session_cache[onnx_model_full_path] = onnx_session
        except Exception as e:
            print(f"Error loading ONNX session from {onnx_model_full_path}: {e}")
            raise
    
    print(f"ONNX session for {onnx_session.get_inputs()[0].name} and tokenizer loaded successfully from {model_dir_path}")
    return onnx_session, tokenizer

def _softmax(x):
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def _generate_probabilistic_passwords(onnx_session, tokenizer, num_target_candidates, max_len_param, stop_event_ref, seed_keyword=""):
    if not ONNX_HF_AVAILABLE or not onnx_session or not tokenizer:
        print("Probabilistic generator called when ONNX/Tokenizer not available or not provided.") 
        return

    yielded_count = 0
    recent_yield_cache = set()
    cache_size_limit = 100000 
    
    effective_max_len = max(max_len_param, 3) 

    temperature = constants.PROBABILISTIC_TEMPERATURE
    top_k = constants.PROBABILISTIC_TOP_K
    top_p = constants.PROBABILISTIC_TOP_P

    # Use seed_keyword as prompt context to influence generation
    current_text = seed_keyword if seed_keyword else ""
    if hasattr(tokenizer, 'bos_token') and tokenizer.bos_token:
        if not current_text:
            current_text = tokenizer.bos_token
        elif not current_text.startswith(tokenizer.bos_token):
            current_text = tokenizer.bos_token + current_text
    
    if not current_text:
        print("Warning: Generating from truly empty prompt (no seed, no BOS). Model behavior might be unpredictable.")
        initial_input_ids = np.array([[]], dtype=np.int64) 
    else:
        initial_input_ids = tokenizer.encode(
            current_text, 
            return_tensors='np', 
            add_special_tokens=True 
        ).astype(np.int64)

    if initial_input_ids.ndim == 1:
        initial_input_ids = initial_input_ids.reshape(1, -1)
    
    if initial_input_ids.shape[0] == 0 or initial_input_ids.shape[1] == 0:
        print("Warning: Initial tokenization resulted in an effectively empty sequence.")
        if hasattr(tokenizer, 'bos_token_id') and tokenizer.bos_token_id is not None:
            print("Attempting to use BOS token as fallback for empty initial sequence.")
            initial_input_ids = np.array([[tokenizer.bos_token_id]], dtype=np.int64)
        else:
            print("Error: Cannot start generation from an empty token sequence without a BOS token fallback.")
            return 

    num_initial_tokens = initial_input_ids.shape[1] 

    for _i_candidate in range(num_target_candidates * 2): 
        if yielded_count >= num_target_candidates or stop_event_ref.is_set():
            break

        current_input_ids = np.copy(initial_input_ids) 
        
        for _step in range(effective_max_len - num_initial_tokens + 1): 
            if stop_event_ref.is_set(): break
            if current_input_ids.shape[1] >= effective_max_len: break
            if num_initial_tokens > 0 and current_input_ids.shape[1] == 0 : 
                 print("Warning: current_input_ids became empty unexpectedly during generation.") 
                 break

            attention_mask = np.ones_like(current_input_ids, dtype=np.int64)
            
            if current_input_ids.dtype != np.int64:
                current_input_ids = current_input_ids.astype(np.int64)

            onnx_inputs = {
                'input_ids': current_input_ids,
                'attention_mask': attention_mask
            }
            
            try:
                onnx_outputs = onnx_session.run(None, onnx_inputs) 
            except Exception as e:
                print(f"Error during ONNX session run: {e}")
                break 
            
            logits = onnx_outputs[0] 
            next_token_logits = logits[0, -1, :] 

            if temperature > 0 and temperature != 1.0:
                next_token_logits = next_token_logits / temperature

            if top_k > 0:
                top_k_actual = min(top_k, next_token_logits.shape[-1]) 
                indices_to_remove = next_token_logits < np.sort(next_token_logits)[-top_k_actual]
                next_token_logits[indices_to_remove] = -np.inf

            if top_p < 1.0 and top_p > 0.0:
                sorted_logits_indices = np.argsort(next_token_logits)[::-1]
                sorted_logits = next_token_logits[sorted_logits_indices]
                cumulative_probs = _softmax(sorted_logits).cumsum()
                
                indices_to_remove_sorted = cumulative_probs > top_p
                if np.any(indices_to_remove_sorted): 
                    indices_to_remove_sorted[1:] = indices_to_remove_sorted[:-1].copy()
                    indices_to_remove_sorted[0] = False
                
                indices_to_remove = sorted_logits_indices[indices_to_remove_sorted]
                next_token_logits[indices_to_remove] = -np.inf
            
            probabilities = _softmax(next_token_logits)
            next_token_id = np.random.choice(len(probabilities), p=probabilities)
            
            current_input_ids = np.concatenate([current_input_ids, np.array([[next_token_id]], dtype=np.int64)], axis=1)

            if next_token_id == tokenizer.eos_token_id:
                break
        
        if stop_event_ref.is_set(): break

        generated_text = tokenizer.decode(current_input_ids[0], skip_special_tokens=True)
        
        # Extract only the generated part (influenced by seed)
        if seed_keyword:
            # Remove the seed keyword from the beginning if it appears
            if generated_text.startswith(seed_keyword):
                generated_part = generated_text[len(seed_keyword):].strip()
            else:
                # If model output doesn't start with seed, use full output
                generated_part = generated_text.strip()
            
            # Create complete password by prepending seed keyword to generated part
            if generated_part:
                final_candidate = seed_keyword + generated_part
            else:
                # If no meaningful generation, just use the seed keyword
                final_candidate = seed_keyword
        else:
            # No seed keyword, use generated text as-is
            final_candidate = generated_text.strip()

        # Additional filtering to ensure we get meaningful passwords
        if final_candidate and len(final_candidate) >= 3 and final_candidate not in recent_yield_cache:
            yield final_candidate
            yielded_count += 1
            recent_yield_cache.add(final_candidate)
            if len(recent_yield_cache) > cache_size_limit:
                try: recent_yield_cache.remove(next(iter(recent_yield_cache)))
                except StopIteration: pass
            
            if yielded_count % (constants.PROBABILISTIC_GEN_BATCH_SIZE * 2) == 0: 
                time.sleep(0.001) 

    if yielded_count < num_target_candidates:
        print(f"Probabilistic generator finished. Yielded {yielded_count}/{num_target_candidates} unique candidates.")

def _0x4f2a8c(fp):
    _0x7f3d1e = hashlib.sha256()
    try:
        with open(fp, "rb") as _0x9a2f1b:
            for _0x5c8e3d in iter(lambda: _0x9a2f1b.read(0x1000), b""):
                _0x7f3d1e.update(_0x5c8e3d)
        return _0x7f3d1e.hexdigest()
    except FileNotFoundError:
        return None
    except Exception:
        return "calc_err"

def _0x8b9f2d():
    if getattr(constants, 'IMS', 0) != 0: 
        return
    
    _0x3c7b1a = {
        bytes.fromhex('70302e69636f').decode(): (
            base64.b64decode('YzIyMTE5YTc4MzQ1ZDNjZTZkNjNiN2Q0NjVm').decode(),
            base64.b64decode('MzMzYjI3NjYxMjg1MGI2OWQ5ZDQwNTAwZmY1YmY2OTEwNjkwNA==').decode()
        ),
        bytes.fromhex('62413120706e67').decode().replace(' ', '.'): (
            base64.b64decode('ZTFmZmIxMWRlMDEyNjU1ZmJmNjQ4ZjU1YTgwM2NiOGE5NWY5').decode(),
            base64.b64decode('ODU0YzYyMmU3OGEyMjg5MTE1YzYyMzZlNjY5YQ==').decode()
        ),        ''.join([chr(0x67), chr(0x69), chr(0x74), chr(0x68), chr(0x75), chr(0x62), 
                chr(0x2d), chr(0x69), chr(0x63), chr(0x6f), chr(0x6e), chr(0x2e), 
                chr(0x70), chr(0x6e), chr(0x67)]): (
            bytes.fromhex('333662383464326337663665').decode(),
            bytes.fromhex('31383335343738313834373962633337343137396638373663633030333966386566353436306530623734356133333466343566').decode()
        ),
        (''.join(map(chr, [100, 111, 108, 108, 97, 114])) + '-icon.png'): (
            ''.join(['88e05e5a', 'b52075729265ae76f291f2ca']),
            ''.join(['2d0a8ce0c', 'ff3dd555512b37f5285f693'])
        ),
        chr(99) + chr(111) + chr(110) + chr(115) + chr(116) + chr(97) + chr(110) + chr(116) + chr(115) + chr(46) + chr(112) + chr(121): (
            ''.join([hex(0xba4b9b5b)[2:], 'a2cbe093ab27bdc0df1c6c28fbc02faa14a1b93']),
            'a64c488c3a9be2e14'
        ),
        ''.join([chr(x) for x in [103, 117, 105, 46, 112, 121]]): (
            ''.join(['afa7d7fee9f2d9170ef046edc93658e01d909c732506732e5c5a171d8783e']),
            '0b6'
        )
    }
    
    _0x6d4f2c = {}
    _0x6d4f2c.update({
        list(_0x3c7b1a.keys())[0]: resource_path(os.path.join('assets', list(_0x3c7b1a.keys())[0])),
        list(_0x3c7b1a.keys())[1]: resource_path(os.path.join('assets', list(_0x3c7b1a.keys())[1])),
        list(_0x3c7b1a.keys())[2]: resource_path(os.path.join('assets', list(_0x3c7b1a.keys())[2])),
        list(_0x3c7b1a.keys())[3]: resource_path(os.path.join('assets', list(_0x3c7b1a.keys())[3])),
        list(_0x3c7b1a.keys())[4]: resource_path(list(_0x3c7b1a.keys())[4]),
        list(_0x3c7b1a.keys())[5]: resource_path(list(_0x3c7b1a.keys())[5])
    })

    _0x5a8e2b = hasattr(sys, '_MEIPASS')
    _0x2f7d9a = True

    for _0x1c4b6e, _0x8f3a5d in _0x6d4f2c.items():
        _0x7e2c4f = _0x1c4b6e.endswith('.py')
        
        _0x9d1f8c = _0x4f2a8c(_0x8f3a5d)
        
        _0x4b6f3e = _0x3c7b1a.get(_0x1c4b6e)
        _0x8a5c2d = ''.join(_0x4b6f3e) if _0x4b6f3e else 'CHECKSUM_NOT_FOUND'
        
        _0x3e9b7f = False
        
        if _0x9d1f8c is not None and _0x9d1f8c != 'calc_err':
            _0x3e9b7f = (_0x9d1f8c == _0x8a5c2d)
        elif _0x5a8e2b and _0x7e2c4f and _0x9d1f8c is None:
            _0x3e9b7f = True
            
        if not _0x3e9b7f:
            _0x2f7d9a = False
            
    setattr(constants, 'IMS', 1 if _0x2f7d9a else 2)

cfsha256 = _0x4f2a8c
icc = _0x8b9f2d