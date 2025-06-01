import argparse
import os
import json
from pathlib import Path
import logging
import shutil
import sys
import tempfile
import time
import math
import random
from collections import Counter, defaultdict
import re

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from datasets import load_dataset, Dataset, DatasetDict
    from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers, Regex
    from transformers import (
        GPT2Config,
        GPT2LMHeadModel,
        PreTrainedTokenizerFast,
        Trainer,
        TrainingArguments,
        DataCollatorForLanguageModeling,
        TrainerCallback,
        trainer_utils,
        GPT2PreTrainedModel,
        GPT2Model
    )
    from transformers.trainer_utils import get_last_checkpoint
    from transformers.modeling_outputs import CausalLMOutputWithCrossAttentions
    import numpy as np

    HF_AVAILABLE = True
except ImportError as e:
    HF_AVAILABLE = False
    print(f"Hugging Face transformers, datasets, tokenizers or PyTorch not found: {e}")
    print("Please install them: pip install transformers datasets tokenizers torch")

try:
    from google.colab import drive
    COLAB_ENV = True
except ImportError:
    COLAB_ENV = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOS_TOKEN = "[BOS]"
EOS_TOKEN = "[EOS]"
UNK_TOKEN = "[UNK]"
PAD_TOKEN = "[PAD]"
SPECIAL_TOKENS = [BOS_TOKEN, EOS_TOKEN, UNK_TOKEN, PAD_TOKEN]

class PatternAnalyzer:
    def __init__(self):
        self.patterns = {
            'digits': re.compile(r'\d+'),
            'letters': re.compile(r'[a-zA-Z]+'),
            'special_chars': re.compile(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+'),
            'uppercase': re.compile(r'[A-Z]+'),
            'lowercase': re.compile(r'[a-z]+'),
            'year_pattern': re.compile(r'(19|20)\d{2}'),
            'common_endings': re.compile(r'(123|456|789|000|111|!+|\?+)$'),
            'common_beginnings': re.compile(r'^(pass|admin|user|test|demo)')
        }
        
        self.ngram_stats = defaultdict(Counter)
        self.complexity_weights = {}
        
    def analyze_password(self, password):
        features = {}
        features['length'] = len(password)
        features['has_digits'] = bool(self.patterns['digits'].search(password))
        features['has_letters'] = bool(self.patterns['letters'].search(password))
        features['has_special'] = bool(self.patterns['special_chars'].search(password))
        features['has_uppercase'] = bool(self.patterns['uppercase'].search(password))
        features['has_lowercase'] = bool(self.patterns['lowercase'].search(password))
        features['has_year'] = bool(self.patterns['year_pattern'].search(password))
        features['common_ending'] = bool(self.patterns['common_endings'].search(password))
        features['common_beginning'] = bool(self.patterns['common_beginnings'].search(password.lower()))
        
        complexity = 0
        if features['has_digits']: complexity += 1
        if features['has_letters']: complexity += 1
        if features['has_special']: complexity += 1
        if features['has_uppercase'] and features['has_lowercase']: complexity += 1
        if features['length'] >= 8: complexity += 1
        if features['length'] >= 12: complexity += 1
        
        features['complexity_score'] = complexity
        return features
    
    def build_ngram_stats(self, passwords):
        logger.info("Building n-gram statistics...")
        for password in passwords:
            for i in range(len(password) - 1):
                self.ngram_stats['bigrams'][password[i:i+2]] += 1
            for i in range(len(password) - 2):
                self.ngram_stats['trigrams'][password[i:i+3]] += 1
                
        logger.info(f"Built statistics: {len(self.ngram_stats['bigrams'])} bigrams, {len(self.ngram_stats['trigrams'])} trigrams")

class CustomGPT2Model(GPT2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.transformer = GPT2Model(config)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        
        self.pattern_embedding = nn.Embedding(10, config.n_embd)
        self.complexity_embedding = nn.Embedding(7, config.n_embd)
        
        self.relative_position_bias = nn.Parameter(torch.zeros(config.n_head, config.n_positions, config.n_positions))
        
        self.pattern_classifier = nn.Sequential(
            nn.Linear(config.n_embd, config.n_embd // 2),
            nn.ReLU(),
            nn.Dropout(config.resid_pdrop),
            nn.Linear(config.n_embd // 2, 10)
        )
        
        self.complexity_predictor = nn.Sequential(
            nn.Linear(config.n_embd, config.n_embd // 4),
            nn.ReLU(),
            nn.Dropout(config.resid_pdrop),
            nn.Linear(config.n_embd // 4, 7)
        )
        
        self.model_parallel = False
        self.device_map = None

        self.post_init()

    def forward(
        self,
        input_ids=None,
        past_key_values=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        encoder_hidden_states=None,
        encoder_attention_mask=None,
        labels=None,
        use_cache=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
        pattern_ids=None,
        complexity_ids=None,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        transformer_outputs = self.transformer(
            input_ids,
            past_key_values=past_key_values,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = transformer_outputs[0]

        if hasattr(self, 'relative_position_bias'):
            seq_len = hidden_states.size(1)
            if seq_len <= self.config.n_positions:
                pos_bias = self.relative_position_bias[:, :seq_len, :seq_len]

        if pattern_ids is not None:
            pattern_embeds = self.pattern_embedding(pattern_ids)
            hidden_states = hidden_states + pattern_embeds.unsqueeze(1)
            
        if complexity_ids is not None:
            complexity_embeds = self.complexity_embedding(complexity_ids)
            hidden_states = hidden_states + complexity_embeds.unsqueeze(1)

        if self.model_parallel:
            torch.cuda.set_device(self.transformer.first_device)
            hidden_states = hidden_states.to(self.lm_head.weight.device)

        lm_logits = self.lm_head(hidden_states)

        loss = None
        pattern_loss = None
        complexity_loss = None
        
        if labels is not None:
            shift_logits = lm_logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            
            loss_fct = nn.CrossEntropyLoss(reduction='none', label_smoothing=0.1)
            flat_shift_logits = shift_logits.view(-1, shift_logits.size(-1))
            flat_shift_labels = shift_labels.view(-1)
            
            ce_loss = loss_fct(flat_shift_logits, flat_shift_labels)
            
            pt = torch.exp(-ce_loss)
            focal_weight = (1 - pt) ** 2
            focal_loss = focal_weight * ce_loss
            
            mask = (flat_shift_labels != -100).float()
            loss = (focal_loss * mask).sum() / mask.sum()
            
            pooled_hidden = hidden_states.mean(dim=1)
            
            pattern_logits = self.pattern_classifier(pooled_hidden)
            complexity_logits = self.complexity_predictor(pooled_hidden)
            
            if pattern_ids is not None:
                pattern_loss = F.cross_entropy(pattern_logits, pattern_ids)
            if complexity_ids is not None:
                complexity_loss = F.cross_entropy(complexity_logits, complexity_ids)
            
            total_loss = loss
            if pattern_loss is not None:
                total_loss = total_loss + 0.1 * pattern_loss
            if complexity_loss is not None:
                total_loss = total_loss + 0.1 * complexity_loss
                
            loss = total_loss

        if not return_dict:
            output = (lm_logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return CausalLMOutputWithCrossAttentions(
            loss=loss,
            logits=lm_logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
            cross_attentions=transformer_outputs.cross_attentions,
        )

class CurriculumCollator(DataCollatorForLanguageModeling):
    def __init__(self, tokenizer, mlm=False, analyzer=None, curriculum_stage=0):
        super().__init__(tokenizer, mlm)
        self.analyzer = analyzer
        self.curriculum_stage = curriculum_stage
        
    def __call__(self, examples):
        if self.analyzer and self.curriculum_stage < 3:
            analyzed_examples = []
            for example in examples:
                if 'input_ids' in example:
                    text = self.tokenizer.decode(example['input_ids'], skip_special_tokens=True)
                    features = self.analyzer.analyze_password(text)
                    analyzed_examples.append((example, features['complexity_score']))
            
            analyzed_examples.sort(key=lambda x: x[1])
            
            if self.curriculum_stage == 0:
                examples = [ex[0] for ex in analyzed_examples[:int(len(analyzed_examples) * 0.6)]]
            elif self.curriculum_stage == 1:
                examples = [ex[0] for ex in analyzed_examples[:int(len(analyzed_examples) * 0.8)]]
            elif self.curriculum_stage == 2:
                examples = [ex[0] for ex in analyzed_examples[:int(len(analyzed_examples) * 0.9)]]
        
        return super().__call__(examples)

class CustomTrainer(Trainer):
    def __init__(self, curriculum_stages=4, **kwargs):
        super().__init__(**kwargs)
        self.curriculum_stages = curriculum_stages
        self.current_stage = 0
        self.steps_per_stage = None
        
    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs)
        loss = outputs.loss
        
        if self.args.max_grad_norm is not None and self.args.max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), self.args.max_grad_norm)
        
        return (loss, outputs) if return_outputs else loss
    
    def _maybe_log_save_evaluate(self, tr_loss, model, trial, epoch, ignore_keys_for_eval):
        if self.steps_per_stage is None and hasattr(self, 'train_dataloader') and self.train_dataloader is not None :
            if len(self.train_dataloader) > 0 :
                total_steps = self.args.num_train_epochs * len(self.train_dataloader)
                if total_steps > 0 and self.curriculum_stages > 0:
                     self.steps_per_stage = total_steps // self.curriculum_stages


        if self.steps_per_stage is not None and self.steps_per_stage > 0 :
            new_stage = min(self.state.global_step // self.steps_per_stage, self.curriculum_stages - 1)
            if new_stage != self.current_stage:
                self.current_stage = new_stage
                logger.info(f"Curriculum learning: Advanced to stage {self.current_stage}")
            
                if hasattr(self.data_collator, 'curriculum_stage'):
                    self.data_collator.curriculum_stage = self.current_stage
        
        return super()._maybe_log_save_evaluate(tr_loss, model, trial, epoch, ignore_keys_for_eval)

def augment_data(passwords, augmentation_factor=1.5):
    augmented = set(passwords)
    
    for password in passwords:
        if len(augmented) >= len(passwords) * augmentation_factor:
            break
            
        variations = []
        
        if password.islower():
            variations.append(password.capitalize())
            variations.append(password.upper())
        
        leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
        leet_version = password
        for char, replacement in leet_map.items():
            if char in leet_version:
                leet_version = leet_version.replace(char, replacement)
                break
        if leet_version != password:
            variations.append(leet_version)
        
        common_suffixes = ['1', '12', '123', '!', '?', '2023', '2024']
        for suffix in common_suffixes:
            if len(password + suffix) <= 20:
                variations.append(password + suffix)
        
        common_prefixes = ['my', 'new', 'old']
        for prefix in common_prefixes:
            if len(prefix + password) <= 20:
                variations.append(prefix + password)
        
        for variation in variations:
            if len(variation) >= 3:
                augmented.add(variation)
    
    logger.info(f"Data augmentation: {len(passwords)} -> {len(augmented)} passwords")
    return list(augmented)

def safe_file_operation(operation, *args, max_retries=3, delay=1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            return operation(*args, **kwargs)
        except (OSError, IOError, PermissionError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"File operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  
            else:
                logger.error(f"File operation failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in file operation: {e}")
            raise

def validate_dataset_files(dataset_paths):
    valid_paths = []
    for path_str in dataset_paths:
        path = Path(path_str)
        if not path.exists():
            logger.error(f"Dataset file not found: {path}")
            continue
        if not path.is_file():
            logger.error(f"Path is not a file: {path}")
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                if not first_line.strip():
                    logger.warning(f"Dataset file appears to be empty: {path}")
                else:
                    valid_paths.append(str(path))
        except Exception as e:
            logger.error(f"Cannot read dataset file {path}: {e}")
    
    if not valid_paths:
        raise ValueError("No valid dataset files found")
    
    logger.info(f"Validated {len(valid_paths)} dataset files")
    return valid_paths

def get_text_iterator(dataset_paths):
    for file_path in dataset_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        stripped_line = line.strip()
                        if stripped_line:  
                            yield stripped_line
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num} in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")

def build_tokenizer(dataset_paths, output_dir_path: Path):
    tokenizer_path = output_dir_path / "tokenizer.json"

    if tokenizer_path.exists():
        logger.info(f"Loading existing tokenizer from {tokenizer_path}")
        try:
            tokenizer = PreTrainedTokenizerFast(
                tokenizer_file=str(tokenizer_path),
                bos_token=BOS_TOKEN,
                eos_token=EOS_TOKEN,
                unk_token=UNK_TOKEN,
                pad_token=PAD_TOKEN,
                model_max_length=512,
            )
            if tokenizer.pad_token is None:
                logger.warning(f"PAD token not loaded correctly from {tokenizer_path}. Rebuilding tokenizer.")
                safe_file_operation(tokenizer_path.unlink, missing_ok=True)
                return build_tokenizer(dataset_paths, output_dir_path)
            return tokenizer
        except Exception as e:
            logger.warning(f"Failed to load tokenizer from {tokenizer_path}: {e}. Rebuilding.")
            safe_file_operation(tokenizer_path.unlink, missing_ok=True)

    logger.info("Building a new character-level tokenizer.")
    try:
        all_chars = set()
        char_count = 0
        for line in get_text_iterator(dataset_paths):
            all_chars.update(line)
            char_count += len(line)
            
        if not all_chars:
            raise ValueError("No characters found in dataset files")
            
        char_list = sorted(list(all_chars))
        logger.info(f"Found {len(char_list)} unique characters from {char_count} total characters")

        core_tokenizer = Tokenizer(models.BPE())
        core_tokenizer.pre_tokenizer = pre_tokenizers.Metaspace()
        core_tokenizer.decoder = decoders.Metaspace()

        bpe_trainer = trainers.BpeTrainer(
            special_tokens=SPECIAL_TOKENS,
            initial_alphabet=char_list,
            vocab_size=len(SPECIAL_TOKENS) + len(char_list)
        )

        logger.info(f"Training tokenizer with {len(char_list)} unique characters and {len(SPECIAL_TOKENS)} special tokens.")
        core_tokenizer.train_from_iterator(get_text_iterator(dataset_paths), trainer=bpe_trainer)

        if PAD_TOKEN not in core_tokenizer.get_vocab():
            core_tokenizer.add_tokens([PAD_TOKEN])
            logger.info(f"Added {PAD_TOKEN} to tokenizer vocab during build.")

        output_dir_path.mkdir(parents=True, exist_ok=True)
        safe_file_operation(core_tokenizer.save, str(tokenizer_path))
        logger.info(f"Character-level tokenizer saved to {tokenizer_path}")

        tokenizer = PreTrainedTokenizerFast(
            tokenizer_file=str(tokenizer_path),
            bos_token=BOS_TOKEN,
            eos_token=EOS_TOKEN,
            unk_token=UNK_TOKEN,
            pad_token=PAD_TOKEN,
            model_max_length=512,
        )
        
        if tokenizer.pad_token_id is None:
            logger.error("PAD token ID is None after building and loading. This will cause issues.")
            pad_token_id_from_vocab = core_tokenizer.token_to_id(PAD_TOKEN)
            if pad_token_id_from_vocab is not None:
                tokenizer.pad_token_id = pad_token_id_from_vocab
                logger.info(f"Manually set PAD token ID to {tokenizer.pad_token_id}")
            else:
                raise RuntimeError(f"Could not find {PAD_TOKEN} in core_tokenizer vocab to set ID.")
        
        return tokenizer
        
    except Exception as e:
        logger.error(f"Failed to build tokenizer: {e}")
        raise

def preprocess_data(examples, tokenizer, max_length=128, analyzer=None):
    try:
        passwords = [f"{BOS_TOKEN}{pw.strip()}{EOS_TOKEN}" for pw in examples["text"]]
        
        padding_strategy = "max_length" if tokenizer.pad_token_id is not None else False
        if tokenizer.pad_token_id is None and padding_strategy == "max_length":
            logger.warning("Tokenizer has no pad_token_id, using no padding instead of max_length")
            padding_strategy = False
            
        model_inputs = tokenizer(
            passwords,
            max_length=max_length,
            truncation=True,
            padding=padding_strategy
        )
        
        if analyzer:
            pattern_ids = []
            complexity_ids = []
            for pw in examples["text"]:
                features = analyzer.analyze_password(pw.strip())
                pattern_id = 0
                if features['has_digits'] and features['has_letters']:
                    pattern_id = 1
                if features['has_special']:
                    pattern_id = 2
                
                pattern_ids.append(pattern_id)
                complexity_ids.append(min(features['complexity_score'], 6))
            
            model_inputs['pattern_ids'] = pattern_ids
            model_inputs['complexity_ids'] = complexity_ids
        
        return model_inputs
    except Exception as e:
        logger.error(f"Error in preprocess_data: {e}")
        raise

def generate_dataset_examples(dataset_paths, apply_augmentation=False):
    total_examples = 0
    all_passwords = []
    
    for file_path_str in dataset_paths:
        file_path = Path(file_path_str)
        logger.info(f"Reading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        stripped_line = line.strip()
                        if stripped_line:
                            all_passwords.append(stripped_line)
                            total_examples += 1
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num} in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
    
    if apply_augmentation and all_passwords:
        logger.info("Applying data augmentation...")
        all_passwords = augment_data(all_passwords)
        total_examples = len(all_passwords)
    
    for password in all_passwords:
        yield {"text": password}
    
    logger.info(f"Generated {total_examples} examples total")

def create_hf_dataset(dataset_paths, cache_dir, apply_augmentation=False):
    logger.info("Attempting to create dataset...")
    
    try:
        logger.info(f"Trying with cache_dir: {cache_dir}")
        full_dataset = Dataset.from_generator(
            generate_dataset_examples,
            gen_kwargs={"dataset_paths": dataset_paths, "apply_augmentation": apply_augmentation},
            cache_dir=str(cache_dir)
        )
        logger.info("Dataset created successfully with cache_dir")
        return full_dataset
    except Exception as e:
        logger.warning(f"Failed to create dataset with cache_dir {cache_dir}: {e}")
    
    try:
        logger.info("Trying without cache_dir...")
        full_dataset = Dataset.from_generator(
            generate_dataset_examples,
            gen_kwargs={"dataset_paths": dataset_paths, "apply_augmentation": apply_augmentation}
        )
        logger.info("Dataset created successfully without cache_dir")
        return full_dataset
    except Exception as e:
        logger.warning(f"Failed to create dataset without cache_dir: {e}")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Trying with temporary cache_dir: {temp_dir}")
            full_dataset = Dataset.from_generator(
                generate_dataset_examples,
                gen_kwargs={"dataset_paths": dataset_paths, "apply_augmentation": apply_augmentation},
                cache_dir=temp_dir
            )
            logger.info("Dataset created successfully with temporary cache_dir")
            return full_dataset
    except Exception as e:
        logger.warning(f"Failed to create dataset with temporary cache_dir: {e}")
    
    try:
        logger.info("Fallback: Creating dataset from list...")
        examples = list(generate_dataset_examples(dataset_paths, apply_augmentation))
        if not examples:
            raise ValueError("No examples generated from dataset files")
        full_dataset = Dataset.from_list(examples)
        logger.info(f"Dataset created successfully from list with {len(examples)} examples")
        return full_dataset
    except Exception as e:
        logger.error(f"All dataset creation methods failed. Last error: {e}")
        raise

def manage_tokenized_cache(dataset, cache_path, operation="save"):
    try:
        if operation == "save" and dataset is not None:
            logger.info(f"Saving tokenized dataset cache to {cache_path}")
            cache_path.mkdir(parents=True, exist_ok=True)
            safe_file_operation(dataset.save_to_disk, str(cache_path))
            logger.info(f"Successfully saved tokenized dataset cache")
            return True
        elif operation == "load":
            if cache_path.exists() and cache_path.is_dir():
                logger.info(f"Loading tokenized dataset cache from {cache_path}")
                try:
                    from datasets import load_from_disk
                    loaded_dataset = load_from_disk(str(cache_path))
                    logger.info(f"Successfully loaded tokenized dataset cache with {len(loaded_dataset)} examples")
                    return loaded_dataset
                except Exception as e:
                    logger.warning(f"Failed to load cached dataset from {cache_path}: {e}")
                    try:
                        shutil.rmtree(cache_path)
                        logger.info(f"Removed corrupted cache directory: {cache_path}")
                    except Exception as cleanup_e:
                        logger.warning(f"Failed to clean up corrupted cache: {cleanup_e}")
                    return None
            else:
                logger.info(f"No tokenized dataset cache found at {cache_path}")
                return None
        else:
            logger.warning(f"Invalid operation '{operation}' for dataset cache")
            return None
    except Exception as e:
        logger.error(f"Error in manage_tokenized_cache ({operation}): {e}")
        return None

def sync_gdrive_directory(gdrive_source_dir: Path, local_target_dir: Path):
    if not COLAB_ENV or not gdrive_source_dir:
        logger.info(f"Skipping sync from GDrive for '{local_target_dir}': Not in Colab or GDrive source path not set/found.")
        return

    try:
        if gdrive_source_dir.is_dir():
            logger.info(f"Syncing from GDrive '{gdrive_source_dir}' to '{local_target_dir}'...")
            shutil.copytree(gdrive_source_dir, local_target_dir, dirs_exist_ok=True)
            logger.info(f"Successfully synced from GDrive")
        else:
            logger.info(f"GDrive source directory '{gdrive_source_dir}' does not exist. Skipping sync.")
    except Exception as e:
        logger.error(f"Failed to sync from GDrive '{gdrive_source_dir}' to '{local_target_dir}': {e}")

class GoogleDriveSync(TrainerCallback):
    def __init__(self, local_output_dir: str, gdrive_sync_target_path: Path, sync_interval_steps: int = 0):
        super().__init__()
        self.local_output_dir = Path(local_output_dir)
        self.gdrive_sync_target_path = gdrive_sync_target_path
        self.sync_interval_steps = sync_interval_steps
        self.last_sync_step = 0

    def on_save(self, args: TrainingArguments, state, control, **kwargs):
        if not COLAB_ENV or not self.gdrive_sync_target_path:
            return
            
        try:
            steps_since_sync = state.global_step - self.last_sync_step
            if self.sync_interval_steps == 0 or steps_since_sync >= self.sync_interval_steps:
                logger.info(f"Syncing to GDrive: {self.local_output_dir} -> {self.gdrive_sync_target_path}")
                self.gdrive_sync_target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(self.local_output_dir, self.gdrive_sync_target_path, dirs_exist_ok=True)
                self.last_sync_step = state.global_step
                logger.info(f"Successfully synced to GDrive at step {state.global_step}")
        except Exception as e:
            logger.warning(f"Failed to sync to GDrive: {e}")

def main():
    if not HF_AVAILABLE:
        logger.error("Required libraries not found. Exiting.")
        sys.exit(1)

    try:
        parser = argparse.ArgumentParser(description="Train an autoregressive Transformer (GPT-style) password model.")
        parser.add_argument("dataset_paths", nargs='+', help="Paths to .txt password dataset files.")
        parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the trained model, tokenizer, and caches.")
        parser.add_argument("--model_name_or_path", type=str, default=None, help="Path to pre-trained model or shortcut name for fine-tuning or resuming.")
        parser.add_argument("--gdrive_cache_dir", type=str, default=None, help="Google Drive directory for backing up the entire output_dir (e.g., '/content/drive/MyDrive/my_project_backup').")
        parser.add_argument("--load_cache_from_gdrive", action="store_true", help="If set, attempts to restore the entire output_dir from --gdrive_cache_dir before training.")
        
        parser.add_argument("--n_layer", type=int, default=6)
        parser.add_argument("--n_head", type=int, default=8)
        parser.add_argument("--n_embd", type=int, default=512)
        parser.add_argument("--dropout_rate", type=float, default=0.15)
        parser.add_argument("--max_seq_length", type=int, default=64)

        parser.add_argument("--num_train_epochs", type=int, default=3)
        parser.add_argument("--per_device_train_batch_size", type=int, default=64)
        parser.add_argument("--per_device_eval_batch_size", type=int, default=64)
        parser.add_argument("--learning_rate", type=float, default=3e-5)
        parser.add_argument("--weight_decay", type=float, default=0.01)
        parser.add_argument("--label_smoothing_factor", type=float, default=0.1)
        parser.add_argument("--max_grad_norm", type=float, default=1.0)
        parser.add_argument("--warmup_steps", type=int, default=500)
        parser.add_argument("--logging_steps", type=int, default=500)
        parser.add_argument("--save_steps", type=int, default=1000)
        parser.add_argument("--eval_steps", type=int, default=1000)
        parser.add_argument("--eval_strategy", type=str, default="steps", choices=["no", "steps", "epoch"])
        parser.add_argument("--fp16", action="store_true", help="Enable mixed precision training.")
        parser.add_argument("--gradient_accumulation_steps", type=int, default=2)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--save_total_limit", type=int, default=2)
        
        parser.add_argument("--use_custom_model", action="store_true", help="Use custom GPT2 model.")
        parser.add_argument("--enable_curriculum", action="store_true", help="Enable curriculum learning.")
        parser.add_argument("--curriculum_stages", type=int, default=4, help="Number of curriculum learning stages.")
        parser.add_argument("--augment_data", action="store_true", help="Apply data augmentation.")
        parser.add_argument("--lr_scheduler_type", type=str, default="cosine", help="Learning rate scheduler type.")
        
        args = parser.parse_args()

        args.dataset_paths = validate_dataset_files(args.dataset_paths)

        output_path = Path(args.output_dir)
        
        gdrive_sync_target_path = None
        if args.gdrive_cache_dir and COLAB_ENV:
            try:
                drive.mount('/content/drive')
                gdrive_sync_target_path = Path(args.gdrive_cache_dir)
                
                if args.load_cache_from_gdrive and gdrive_sync_target_path.exists():
                    logger.info(f"Attempting to restore output_dir from GDrive: {gdrive_sync_target_path}")
                    sync_gdrive_directory(gdrive_sync_target_path, output_path)
                else:
                    logger.info(f"GDrive sync configured but not loading cache (load_cache_from_gdrive={args.load_cache_from_gdrive}, exists={gdrive_sync_target_path.exists() if gdrive_sync_target_path else False})")
            except Exception as e:
                logger.warning(f"Google Drive setup failed: {e}")
                gdrive_sync_target_path = None

        output_path.mkdir(parents=True, exist_ok=True)
        if args.gdrive_cache_dir and not COLAB_ENV:
            logger.info("Google Drive operations (--gdrive_cache_dir) are configured but not in Colab. Skipping GDrive sync.")

        generator_cache_dir = output_path / "generator_cache"
        generator_cache_dir.mkdir(parents=True, exist_ok=True)

        analyzer = PatternAnalyzer()
        if args.use_custom_model:
            logger.info("Building pattern statistics...")
            all_passwords = list(get_text_iterator(args.dataset_paths))
            analyzer.build_ngram_stats(all_passwords)

        tokenizer = build_tokenizer(args.dataset_paths, output_path)
        vocab_size = tokenizer.vocab_size
        logger.info(f"Tokenizer loaded/built. Vocab size: {vocab_size}. PAD ID: {tokenizer.pad_token_id}")
        
        if tokenizer.pad_token_id is None:
            logger.error("CRITICAL: Tokenizer PAD token ID is None. This will likely cause errors in DataCollator or training.")

        tokenized_train_cache_dir = output_path / "tokenized_train_data"
        tokenized_validation_cache_dir = output_path / "tokenized_validation_data"
        
        existing_train_cache = manage_tokenized_cache(None, tokenized_train_cache_dir, "load")
        existing_val_cache = manage_tokenized_cache(None, tokenized_validation_cache_dir, "load")
        
        if existing_train_cache is not None and len(existing_train_cache) > 0:
            logger.info(f"Found existing tokenized training cache with {len(existing_train_cache)} examples. Skipping dataset creation and tokenization.")
            tokenized_train_dataset = existing_train_cache
            
            if existing_val_cache is not None and len(existing_val_cache) > 0:
                logger.info(f"Found existing tokenized validation cache with {len(existing_val_cache)} examples.")
                tokenized_validation_dataset = existing_val_cache
            else:
                logger.info("No validation cache found, creating empty validation dataset.")
                empty_schema_dict = {'input_ids': [], 'attention_mask': []}
                if args.use_custom_model:
                    empty_schema_dict['pattern_ids'] = []
                    empty_schema_dict['complexity_ids'] = []
                tokenized_validation_dataset = Dataset.from_dict(empty_schema_dict)
        else:
            logger.info("No existing tokenized cache found. Loading and preprocessing datasets...")
            full_dataset = create_hf_dataset(args.dataset_paths, generator_cache_dir, args.augment_data)
            raw_datasets = DatasetDict({"train": full_dataset})
            logger.info(f"Loaded {len(raw_datasets['train'])} examples.")

            if len(raw_datasets["train"]) == 0:
                logger.error("Train dataset is empty. Cannot proceed.")
                sys.exit(1)
            
            test_size_for_split = 0.15
            try:
                if len(raw_datasets["train"]) < 10: 
                    logger.warning(f"Train dataset has only {len(raw_datasets['train'])} samples. Validation split might be very small or empty.")
                    if len(raw_datasets["train"]) < 2: 
                        logger.warning("Cannot create a validation split with less than 2 samples. Skipping validation.")
                        empty_test_data = {"text": []}
                        train_val_split = {"train": raw_datasets["train"], "test": Dataset.from_dict(empty_test_data)} 
                    else:
                        train_val_split = raw_datasets["train"].train_test_split(test_size=test_size_for_split, seed=args.seed, shuffle=True)
                else:
                    train_val_split = raw_datasets["train"].train_test_split(test_size=test_size_for_split, seed=args.seed, shuffle=True)
            except Exception as e:
                logger.error(f"Failed to split dataset: {e}")
                empty_test_data = {"text": []}
                train_val_split = {"train": raw_datasets["train"], "test": Dataset.from_dict(empty_test_data)}

            preprocess_fn_kwargs = {
                "tokenizer": tokenizer, 
                "max_length": args.max_seq_length,
                "analyzer": analyzer if args.use_custom_model else None
            }

            logger.info("Tokenizing training data...")
            try:
                tokenized_train_dataset = train_val_split['train'].map(
                    preprocess_data, batched=True,
                    fn_kwargs=preprocess_fn_kwargs,
                    remove_columns=train_val_split['train'].column_names
                )
                manage_tokenized_cache(tokenized_train_dataset, tokenized_train_cache_dir, "save")
            except Exception as e:
                logger.error(f"Failed to tokenize training data: {e}")
                raise

            if len(train_val_split['test']) > 0:
                logger.info("Tokenizing validation data...")
                try:
                    tokenized_validation_dataset = train_val_split['test'].map(
                        preprocess_data, batched=True,
                        fn_kwargs=preprocess_fn_kwargs,
                        remove_columns=train_val_split['test'].column_names
                    )
                    manage_tokenized_cache(tokenized_validation_dataset, tokenized_validation_cache_dir, "save")
                except Exception as e:
                    logger.warning(f"Failed to tokenize validation data: {e}. Creating empty validation dataset.")
                    empty_schema_dict = {'input_ids': [], 'attention_mask': []}
                    if args.use_custom_model:
                        empty_schema_dict['pattern_ids'] = []
                        empty_schema_dict['complexity_ids'] = []
                    tokenized_validation_dataset = Dataset.from_dict(empty_schema_dict)
            else:
                logger.info("Validation split is empty. Creating an empty tokenized validation dataset.")
                empty_schema_dict = {'input_ids': [], 'attention_mask': []}
                if args.use_custom_model:
                    empty_schema_dict['pattern_ids'] = []
                    empty_schema_dict['complexity_ids'] = []
                tokenized_validation_dataset = Dataset.from_dict(empty_schema_dict)

        tokenized_datasets = DatasetDict({
            'train': tokenized_train_dataset,
            'validation': tokenized_validation_dataset
        })
        logger.info(f"Dataset structure: train={len(tokenized_datasets['train'])}, validation={len(tokenized_datasets['validation'])}")

        try:
            existing_model_path = output_path / "pytorch_model.bin"
            existing_config_path = output_path / "config.json"
            
            model_to_load_from = None
            if args.model_name_or_path and Path(args.model_name_or_path).is_dir():
                 model_to_load_from = args.model_name_or_path
                 logger.info(f"Loading model from specified path: {model_to_load_from}")
            elif existing_model_path.exists() and existing_config_path.exists():
                 model_to_load_from = str(output_path)
                 logger.info(f"Found existing model in output directory. Loading from: {model_to_load_from}")
            elif args.model_name_or_path:
                 model_to_load_from = args.model_name_or_path # Hub name
                 logger.info(f"Attempting to load model from Hugging Face Hub: {model_to_load_from}")


            if model_to_load_from:
                if args.use_custom_model:
                    model = CustomGPT2Model.from_pretrained(model_to_load_from)
                else:
                    model = GPT2LMHeadModel.from_pretrained(model_to_load_from)
                if model.config.vocab_size != vocab_size:
                    logger.warning(f"Model vocab size ({model.config.vocab_size}) and tokenizer vocab size ({vocab_size}) mismatch. Resizing model embeddings.")
                    model.resize_token_embeddings(len(tokenizer))
            else:
                logger.info(f"Initializing a new {'Custom ' if args.use_custom_model else ''}GPT-2 style model.")
                config = GPT2Config(
                    vocab_size=vocab_size,
                    n_positions=args.max_seq_length,
                    n_embd=args.n_embd,
                    n_layer=args.n_layer,
                    n_head=args.n_head,
                    bos_token_id=tokenizer.bos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    resid_pdrop=args.dropout_rate,
                    embd_pdrop=args.dropout_rate,
                    attn_pdrop=args.dropout_rate,
                )
                if args.use_custom_model:
                    model = CustomGPT2Model(config)
                else:
                    model = GPT2LMHeadModel(config)
        except Exception as e:
            logger.error(f"Failed to load/create model: {e}")
            raise

        logger.info(f"Model initialized. Number of parameters: {model.num_parameters():,}")

        can_evaluate = len(tokenized_datasets["validation"]) > 0 and tokenized_datasets["validation"].num_rows > 0
        
        training_args_dict = {
            "output_dir": str(output_path),
            "overwrite_output_dir": False, 
            "num_train_epochs": args.num_train_epochs,
            "per_device_train_batch_size": args.per_device_train_batch_size,
            "per_device_eval_batch_size": args.per_device_eval_batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "label_smoothing_factor": args.label_smoothing_factor,
            "max_grad_norm": args.max_grad_norm,
            "warmup_steps": args.warmup_steps,
            "lr_scheduler_type": args.lr_scheduler_type,
            "logging_dir": str(output_path / "logs"),
            "logging_steps": args.logging_steps,
            "save_steps": args.save_steps,
            "save_total_limit": args.save_total_limit,
            "fp16": args.fp16,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "seed": args.seed,
            "report_to": "tensorboard",
            "dataloader_pin_memory": True,
            "dataloader_num_workers": 2 if os.name != 'nt' else 0, # num_workers > 0 can cause issues on Windows
            "remove_unused_columns": False,
        }

        user_wants_evaluation = args.eval_strategy != "no"

        if can_evaluate and user_wants_evaluation:
            training_args_dict["do_eval"] = True
            training_args_dict["eval_strategy"] = args.eval_strategy
            logger.info("Setting 'do_eval = True' for evaluation.")
            if args.eval_strategy == "steps":
                training_args_dict["eval_steps"] = args.eval_steps
        else:
            training_args_dict["do_eval"] = False
            logger.info("Setting 'do_eval = False' as evaluation is disabled or not possible.")
            
        logger.info(f"Initializing TrainingArguments with parameters: {training_args_dict}")
        training_args = TrainingArguments(**training_args_dict)
        
        try:
            if args.enable_curriculum:
                data_collator = CurriculumCollator(
                    tokenizer=tokenizer, 
                    mlm=False, 
                    analyzer=analyzer,
                    curriculum_stage=0
                )
                logger.info("Using curriculum collator")
            else:
                data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
                logger.info("Using standard data collator")
        except Exception as e:
            logger.error(f"Failed to create data collator: {e}")
            raise

        try:
            trainer_cls = CustomTrainer if args.enable_curriculum else Trainer
            trainer_init_kwargs = {
                "model": model,
                "args": training_args,
                "train_dataset": tokenized_datasets["train"] if len(tokenized_datasets['train']) > 0 else None,
                "eval_dataset": tokenized_datasets["validation"] if can_evaluate and user_wants_evaluation else None, 
                "tokenizer": tokenizer, 
                "data_collator": data_collator,
            }
            if args.enable_curriculum:
                trainer_init_kwargs["curriculum_stages"] = args.curriculum_stages
                logger.info(f"Using custom trainer with {args.curriculum_stages} stages")
            else:
                logger.info("Using standard trainer")

            trainer = trainer_cls(**trainer_init_kwargs)
            
        except Exception as e:
            logger.error(f"Failed to create trainer: {e}")
            raise

        if gdrive_sync_target_path and COLAB_ENV:
            gdrive_callback = GoogleDriveSync(
                local_output_dir=str(output_path),
                gdrive_sync_target_path=gdrive_sync_target_path,
                sync_interval_steps=5000
            )
            trainer.add_callback(gdrive_callback)
            logger.info("Added Google Drive sync callback")

        resume_arg_for_trainer = None 
        try:
            # Prioritize explicit model_name_or_path if it's a checkpoint dir
            if args.model_name_or_path:
                model_path_obj = Path(args.model_name_or_path)
                if model_path_obj.is_dir() and (model_path_obj / "trainer_state.json").exists():
                    resume_arg_for_trainer = str(model_path_obj)
                    logger.info(f"Attempting to resume from specified checkpoint: {resume_arg_for_trainer}")

            # Fallback to last checkpoint in output_dir if not resuming from model_name_or_path
            if not resume_arg_for_trainer:
                last_checkpoint_in_output_dir = get_last_checkpoint(args.output_dir)
                if last_checkpoint_in_output_dir:
                    resume_arg_for_trainer = last_checkpoint_in_output_dir
                    logger.info(f"Found existing checkpoint in output directory to resume from: {last_checkpoint_in_output_dir}")
        except Exception as e: # Broad exception as get_last_checkpoint can fail if dir is malformed
            logger.warning(f"Error checking for existing checkpoints: {e}. Starting fresh or from model_name_or_path if it's not a checkpoint.")


        logger.info(f"Starting model training with:")
        logger.info(f"  - Custom model: {args.use_custom_model}")
        logger.info(f"  - Curriculum learning: {args.enable_curriculum}")
        logger.info(f"  - Data augmentation: {args.augment_data}")
        logger.info(f"  - Resume from checkpoint: {resume_arg_for_trainer}")
        logger.info(f"  - Training samples: {len(tokenized_datasets['train'])}")
        logger.info(f"  - Validation samples: {len(tokenized_datasets['validation'])}")
        
        try:
            train_result = trainer.train(resume_from_checkpoint=resume_arg_for_trainer)
            
            safe_file_operation(trainer.save_model)
            safe_file_operation(trainer.save_state)
            
            metrics = train_result.metrics
            metrics["train_samples"] = len(tokenized_datasets["train"])
            trainer.log_metrics("train", metrics)
            trainer.save_metrics("train", metrics)
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            try:
                trainer.save_model()
                logger.info("Model saved despite training failure")
            except:
                logger.error("Could not save model after training failure")
            raise

        if gdrive_sync_target_path and COLAB_ENV:
            try:
                logger.info(f"Final sync to GDrive: {output_path} -> {gdrive_sync_target_path}")
                gdrive_sync_target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(output_path, gdrive_sync_target_path, dirs_exist_ok=True)
                logger.info("Final sync to GDrive completed successfully")
            except Exception as e:
                logger.warning(f"Final sync to GDrive failed: {e}")

        logger.info("Training complete.")
        logger.info(f"Model, tokenizer, and training state saved to {args.output_dir}")

        if can_evaluate and user_wants_evaluation:
            try:
                logger.info("Evaluating final model...")
                eval_metrics = trainer.evaluate()
                logger.info(f"Evaluation metrics: {eval_metrics}")
                trainer.log_metrics("eval", eval_metrics)
                trainer.save_metrics("eval", eval_metrics)
            except Exception as e:
                logger.warning(f"Final evaluation failed: {e}")
        else:
            logger.info("Skipping final evaluation as validation set is empty or evaluation was disabled.")

    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()