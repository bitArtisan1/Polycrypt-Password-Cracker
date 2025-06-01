import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog as tkfiledialog
import threading
import time
import customtkinter
import platform
import os
from datetime import datetime
import random
import string
from PIL import Image
import webbrowser

if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            print(f"Could not set DPI awareness (user32): {e}")
    except Exception as e:
        print(f"Could not set DPI awareness (shcore): {e}")


import constants
import utils
import logic
import rainbow_tables

root = None
target_hash_entry = None
hash_type_combo = None
attack_mode_var = None
wordlist_path_entry = None
max_wordlist_length_entry = None
charset_entry = None
bf_min_len_entry = None
bf_max_len_entry = None
rule_wordlist_path_entry = None
max_candidate_length_entry = None
rule_capitalize_var = None
rule_append_numbers_var = None
rule_leet_speak_var = None
rule_toggle_case_var = None
rule_reverse_word_var = None
rule_prepend_append_common_var = None
probabilistic_model_path_entry = None
probabilistic_num_candidates_entry = None
probabilistic_max_len_entry = None
probabilistic_seed_keyword_entry = None
result_text = None
progressbar = None
speed_label = None
crack_button = None
stop_button = None
status_label = None
eta_label = None

save_to_rainbow_table_var = None

wordlist_options_frame = None
bruteforce_options_frame = None
rule_based_options_frame = None
probabilistic_options_frame = None
rainbow_table_options_frame = None
separator_options = None

rainbow_table_import_wordlist_entry = None
rainbow_table_import_algorithms_var = None
rainbow_table_export_path_entry = None
rainbow_table_stats_text = None

crack_thread = None
app_start_time = time.time()
animation_active = False

_last_scheduled_ui_update_time = 0.0
UI_UPDATE_THROTTLE_INTERVAL = 0.0

_last_detailed_log_time = 0.0
DETAILED_LOG_INTERVAL = 0.1

_last_progress_update_time = 0.0
PROGRESS_UPDATE_INTERVAL = 0.5

_offset_x = 0
_offset_y = 0

_glitch_animation_id = None
_active_glitch_tags = []
_glitch_char_set = string.punctuation + string.ascii_letters + string.digits + "█▓▒░"
_glitch_tag_counter = 0
GLITCH_ANIMATION_INTERVAL = 75


pulse_animation_id = None
current_pulse_color = constants.PULSE_COLOR_1

current_pulse_color = constants.PULSE_COLOR_1

def generate_random_glitch_chars(length=3):
    return "".join(random.choice(_glitch_char_set) for _ in range(length))

def animate_glitching_text_effects():
    global _glitch_animation_id, _active_glitch_tags, result_text, root

    if not root or not root.winfo_exists() or not result_text or not result_text.winfo_exists():
        _glitch_animation_id = None
        _active_glitch_tags.clear()
        return

    if not _active_glitch_tags:
        _glitch_animation_id = None
        return

    tags_to_remove_from_active_list = []

    result_text.configure(state="normal")
    for tag_name in list(_active_glitch_tags):
        try:
            current_ranges = result_text.tag_ranges(tag_name)
            if not current_ranges:
                tags_to_remove_from_active_list.append(tag_name)
                continue
            
            new_glitch_str = generate_random_glitch_chars(3)
            
            start_index = result_text.index(f"{tag_name}.first")
            end_index = result_text.index(f"{tag_name}.last")
            if start_index and end_index:
                result_text.delete(start_index, end_index)
                result_text.insert(start_index, new_glitch_str, tag_name)
            else:
                tags_to_remove_from_active_list.append(tag_name)

        except tk.TclError:
            tags_to_remove_from_active_list.append(tag_name)
        except Exception as e:
            print(f"Error animating glitch tag {tag_name}: {e}")
            tags_to_remove_from_active_list.append(tag_name)

    result_text.configure(state="disabled")

    for tag_name in tags_to_remove_from_active_list:
        if tag_name in _active_glitch_tags:
            _active_glitch_tags.remove(tag_name)

    if _active_glitch_tags:
        _glitch_animation_id = root.after(GLITCH_ANIMATION_INTERVAL, animate_glitching_text_effects)
    else:
        _glitch_animation_id = None

def start_glitch_animation_if_needed():
    global _glitch_animation_id
    if not _glitch_animation_id and _active_glitch_tags:
        animate_glitching_text_effects()

def log_with_timestamp(message, message_type="INFO"):
    global result_text, root, _glitch_tag_counter, _active_glitch_tags
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if result_text and result_text.winfo_exists():
        result_text.configure(state="normal")

        if message_type == "SUCCESS_GLITCH":
            _glitch_tag_counter += 1
            left_tag = f"glitch_left_{_glitch_tag_counter}"
            _glitch_tag_counter += 1
            right_tag = f"glitch_right_{_glitch_tag_counter}"

            prefix_text = f"" 
            result_text.insert(tk.END, prefix_text, ("log_success_color",))
            result_text.tag_configure("log_success_color", foreground=constants.SUCCESS_COLOR)
            
            initial_left_glitch = generate_random_glitch_chars(3)
            result_text.insert(tk.END, initial_left_glitch, (left_tag, "log_success_color"))
            result_text.tag_configure(left_tag, foreground=constants.SUCCESS_COLOR)
            
            result_text.insert(tk.END, f" {message} ", ("log_success_color",))
            
            initial_right_glitch = generate_random_glitch_chars(3)
            result_text.insert(tk.END, initial_right_glitch, (right_tag, "log_success_color"))
            result_text.tag_configure(right_tag, foreground=constants.SUCCESS_COLOR)
            
            result_text.insert(tk.END, "\n")

            _active_glitch_tags.append(left_tag)
            _active_glitch_tags.append(right_tag)
            start_glitch_animation_if_needed()
        
        elif message_type == "RESULT":
            prefix_text = f"" 
            result_text.insert(tk.END, prefix_text, ("log_success_color",))
            result_text.tag_configure("log_success_color", foreground=constants.SUCCESS_COLOR)
            
            result_text.insert(tk.END, f"{message} ", ("log_success_color",))

            result_text.insert(tk.END, "\n")

        else:
            color_map = {
                "INFO": constants.FG_COLOR,
                "SUCCESS": constants.SUCCESS_COLOR,
                "ERROR": constants.ERROR_COLOR,
                "WARNING": constants.WARNING_COLOR,
                "SYSTEM": constants.FG_COLOR
            }
            
            text_color_to_apply = color_map.get(message_type, constants.FG_COLOR)
            
            prefix_map = {
                "INFO": "▶",
                "SUCCESS": "✓",
                "ERROR": "✗",
                "WARNING": "⚠",
                "SYSTEM": "◉"
            }
            prefix = prefix_map.get(message_type, "▶")
            
            _glitch_tag_counter += 1
            log_entry_color_tag = f"log_color_{message_type.lower()}_{_glitch_tag_counter}"
            result_text.tag_configure(log_entry_color_tag, foreground=text_color_to_apply)
            
            formatted_message = f"[{timestamp}] {prefix} {message}\n"
            result_text.insert(tk.END, formatted_message, (log_entry_color_tag,))

        result_text.see(tk.END)
        result_text.configure(state="disabled")

def animate_pulse():
    global pulse_animation_id, current_pulse_color, animation_active
    
    if not animation_active or not progressbar or not progressbar.winfo_exists():
        return
    
    if current_pulse_color == constants.PULSE_COLOR_1:
        current_pulse_color = constants.PULSE_COLOR_2
    else:
        current_pulse_color = constants.PULSE_COLOR_1
    
    try:
        progressbar.configure(progress_color=current_pulse_color)
    except:
        pass
    
    pulse_animation_id = root.after(800, animate_pulse)

def start_pulse_animation():
    global animation_active
    animation_active = True
    animate_pulse()

def stop_pulse_animation():
    global animation_active, pulse_animation_id
    animation_active = False
    if pulse_animation_id:
        root.after_cancel(pulse_animation_id)
        pulse_animation_id = None
    
    if progressbar and progressbar.winfo_exists():
        progressbar.configure(progress_color=constants.PROGRESS_BAR_COLOR)

def create_tooltip(widget, text):
    def on_enter(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.configure(bg=constants.BUTTON_BG_COLOR, highlightbackground=constants.HIGHLIGHT_COLOR, highlightthickness=1)
        
        label = tk.Label(tooltip, text=text, 
                        bg=constants.BUTTON_BG_COLOR, 
                        fg=constants.FG_COLOR,
                        font=constants.FONT_FAMILY_UI,
                        padx=8, pady=4)
        label.pack()
        
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        tooltip.geometry(f"+{x}+{y}")
        
        widget.tooltip = tooltip
    
    def on_leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

def on_title_bar_press(event):
    global _offset_x, _offset_y
    _offset_x = event.x
    _offset_y = event.y

def on_title_bar_drag(event):
    global root
    x = root.winfo_pointerx() - _offset_x
    y = root.winfo_pointery() - _offset_y
    root.geometry(f"+{x}+{y}")

def minimize_window():
    global root
    if platform.system() == "Windows":
        root.overrideredirect(False)
        root.iconify()
    else:
        try: 
            root.iconify()
        except tk.TclError: 
            root.withdraw()

def on_deiconify(event=None):
    global root
    if root.state() == 'normal' and not root.overrideredirect():
        root.after(50, lambda: root.overrideredirect(True))

def calculate_eta(current, total, elapsed_time):
    if current == 0 or total == 0:
        return "Calculating..."
    
    rate = current / elapsed_time
    if rate == 0:
        return "Unknown"
    
    remaining = total - current
    eta_seconds = remaining / rate
    
    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    elif eta_seconds < 3600:
        return f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
    else:
        hours = int(eta_seconds // 3600)
        minutes = int((eta_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def on_crack_button_click(stop_event_ref):
    global crack_thread, app_start_time
    global target_hash_entry, hash_type_combo, attack_mode_var, wordlist_path_entry, max_wordlist_length_entry
    global charset_entry, bf_min_len_entry, bf_max_len_entry, rule_wordlist_path_entry, max_candidate_length_entry
    global rule_capitalize_var, rule_append_numbers_var, rule_leet_speak_var, rule_toggle_case_var, rule_reverse_word_var, rule_prepend_append_common_var
    global probabilistic_model_path_entry, probabilistic_num_candidates_entry, probabilistic_max_len_entry, probabilistic_seed_keyword_entry
    global result_text, progressbar, speed_label, crack_button, stop_button, root, status_label, eta_label
    global save_to_rainbow_table_var
    global _last_scheduled_ui_update_time, _last_detailed_log_time

    if crack_thread and crack_thread.is_alive():
        messagebox.showwarning("Operation in Progress", "A cracking operation is already running.", parent=root)
        return

    target_hash = target_hash_entry.get().strip()
    selected_hash_type = hash_type_combo.get()
    attack_mode = attack_mode_var.get()
    attack_params = {}

    current_save_to_rainbow_value = False
    if save_to_rainbow_table_var and hasattr(save_to_rainbow_table_var, 'get'):
        current_save_to_rainbow_value = save_to_rainbow_table_var.get()
        log_with_timestamp(f"GUI: save_to_rainbow_table_var.get() returned: {current_save_to_rainbow_value}", "SYSTEM")
    else:
        log_with_timestamp(f"GUI: save_to_rainbow_table_var is problematic or None. Type: {type(save_to_rainbow_table_var)}. Defaulting save_to_rainbow to True.", "WARNING")
        current_save_to_rainbow_value = True

    attack_params["save_to_rainbow"] = current_save_to_rainbow_value

    log_with_timestamp(f"GUI: 'Save to Rainbow Table' checkbox effective value: {'CHECKED' if current_save_to_rainbow_value else 'UNCHECKED'}.", "SYSTEM")
    log_with_timestamp(f"GUI: attack_params['save_to_rainbow'] initially set to: {attack_params['save_to_rainbow']}", "SYSTEM")
    
    if not target_hash:
        messagebox.showerror("Input Error", "Target hash cannot be empty.", parent=root)
        return

    if attack_mode == "Wordlist":
        wordlist_path = wordlist_path_entry.get().strip()
        if not wordlist_path: 
            messagebox.showerror("Configuration Error", "Please specify a wordlist file for the Wordlist Attack.", parent=root)
            return
        try:
            max_len_str = max_wordlist_length_entry.get().strip()
            max_word_len = int(max_len_str) if max_len_str else 0
            if max_word_len < 0: 
                messagebox.showerror("Input Error", "Maximum password length cannot be negative.", parent=root)
                return
            attack_params["wordlist_path"] = wordlist_path
            attack_params["max_word_len"] = max_word_len
        except ValueError: 
            messagebox.showerror("Input Error", "Maximum password length must be a valid number.", parent=root)
            return
    
    elif attack_mode == "Brute-Force":
        charset = charset_entry.get()
        if not charset: 
            messagebox.showerror("Configuration Error", "Character set cannot be empty for Brute-Force Attack.", parent=root)
            return
        try:
            min_len = int(bf_min_len_entry.get().strip())
            max_len = int(bf_max_len_entry.get().strip())
            if not (0 < min_len <= max_len): 
                messagebox.showerror("Input Error", "Invalid length range. Minimum must be positive and not exceed maximum.", parent=root)
                return
            if max_len > 10: 
                if not messagebox.askyesno("Performance Warning", 
                    f"Maximum length of {max_len} may result in extremely long processing times.\n\nDo you want to continue?", 
                    parent=root): 
                    return
            attack_params["charset"] = charset
            attack_params["min_len"] = min_len
            attack_params["max_len"] = max_len
        except ValueError: 
            messagebox.showerror("Input Error", "Length values must be valid integers.", parent=root)
            return
    
    elif attack_mode == "Rule-Based":
        wordlist_path = rule_wordlist_path_entry.get().strip()
        if not wordlist_path: 
            messagebox.showerror("Configuration Error", "Please specify a wordlist file for Rule-Based Attack.", parent=root)
            return
        try:
            max_len_str = max_candidate_length_entry.get().strip()
            max_cand_len = int(max_len_str) if max_len_str else 0
            if max_cand_len < 0: 
                messagebox.showerror("Input Error", "Maximum candidate length cannot be negative.", parent=root)
                return
            rules_config = {
                "capitalize_first": rule_capitalize_var.get(), 
                "append_numbers": rule_append_numbers_var.get(),
                "leet_speak": rule_leet_speak_var.get(), 
                "toggle_case": rule_toggle_case_var.get(),
                "reverse_word": rule_reverse_word_var.get(), 
                "prepend_append_common": rule_prepend_append_common_var.get()
            }
            if not any(rules_config.values()): 
                messagebox.showwarning("Configuration Warning", "Please select at least one transformation rule.", parent=root)
                return
            attack_params["wordlist_path"] = wordlist_path
            attack_params["max_candidate_len"] = max_cand_len
            attack_params["rules"] = rules_config
        except ValueError: 
            messagebox.showerror("Input Error", "Maximum candidate length must be a valid number.", parent=root)
            return
    
    elif attack_mode == "Probabilistic":
        if not utils.ONNX_HF_AVAILABLE:
            messagebox.showerror("Dependency Error", "Probabilistic mode requires ONNX Runtime and Hugging Face Transformers libraries.\nPlease ensure they are installed and a model is exported to ONNX.", parent=root)
            return
        model_dir_path = probabilistic_model_path_entry.get().strip()
        if not model_dir_path: 
            messagebox.showerror("Configuration Error", "Please specify the model directory path.", parent=root)
            return
        if not os.path.isdir(model_dir_path): 
            messagebox.showerror("Path Error", f"The specified model path does not exist:\n{model_dir_path}", parent=root)
            return
        try:
            num_candidates_str = probabilistic_num_candidates_entry.get().strip()
            num_candidates = int(num_candidates_str) if num_candidates_str else constants.DEFAULT_PROBABILISTIC_CANDIDATES
            if num_candidates <= 0: 
                messagebox.showerror("Input Error", "Number of candidates must be positive.", parent=root)
                return
            max_len_str = probabilistic_max_len_entry.get().strip()
            max_len = int(max_len_str) if max_len_str else constants.DEFAULT_PROBABILISTIC_MAX_LEN
            if max_len <= 0: 
                messagebox.showerror("Input Error", "Maximum generation length must be positive.", parent=root)
                return
            seed_keyword = probabilistic_seed_keyword_entry.get().strip()
            attack_params["model_dir_path"] = model_dir_path
            attack_params["num_candidates"] = num_candidates
            attack_params["max_len"] = max_len
            attack_params["seed_keyword"] = seed_keyword
        except ValueError: 
            messagebox.showerror("Input Error", "Numeric values must be valid integers.", parent=root)
            return
        
    elif attack_mode == "Rainbow Table":
        log_with_timestamp("Rainbow table lookup selected. Using existing attack_params.", "INFO")
        
    log_with_timestamp(f"GUI: Final attack_params before calling logic: {attack_params}", "SYSTEM")

    result_text.configure(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.configure(state="disabled")
    
    log_with_timestamp("Initializing cracking operation...", "SYSTEM")
    log_with_timestamp(f"Target Hash: {target_hash[:32]}{'...' if len(target_hash) > 32 else ''}", "INFO")
    log_with_timestamp(f"Attack Mode: {attack_mode}", "INFO")
    log_with_timestamp(f"Hash Type: {selected_hash_type}", "INFO")
    
    progressbar.set(0)
    speed_label.configure(text="Speed: Initializing...")
    status_label.configure(text="Status: Starting operation...")
    eta_label.configure(text="ETA: Calculating...")
    
    crack_button.configure(state=tk.DISABLED, text="OPERATION RUNNING")
    stop_button.configure(state=tk.NORMAL)
    
    stop_event_ref.clear()
    app_start_time = time.time()
    _last_scheduled_ui_update_time = 0.0
    _last_detailed_log_time = 0.0
    start_pulse_animation()

    def update_ui_from_thread(current, total, message, append_message=True, speed=0.0):
     global root, _last_scheduled_ui_update_time, app_start_time, _last_detailed_log_time, _last_progress_update_time

     def _update_task():
        global progressbar, result_text, speed_label, status_label, eta_label, _last_detailed_log_time, _last_progress_update_time
        
        if not root or not root.winfo_exists(): return

        current_time = time.time()
        
        should_update_progress = (current_time - _last_progress_update_time) > PROGRESS_UPDATE_INTERVAL
        
        if should_update_progress:
            _last_progress_update_time = current_time
            
            if total > 0 and total <= constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS:
                progress = current / total if total > 0 else 0
                if progressbar and progressbar.winfo_exists(): progressbar.set(progress)
            elif total > constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS:
                progress = min(current, constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS) / constants.MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS
                if progressbar and progressbar.winfo_exists(): progressbar.set(progress)
            
            if speed > 0:
                if speed_label and speed_label.winfo_exists():
                    if speed >= 1000000:
                        speed_text = f"Speed: {speed/1000000:.2f}M att/sec"
                    elif speed >= 1000:
                        speed_text = f"Speed: {speed/1000:.2f}K att/sec"
                    else:
                        speed_text = f"Speed: {speed:.2f} att/sec"
                    speed_label.configure(text=speed_text)
                
                if status_label and status_label.winfo_exists() and current > 0 and total > 0:
                    progress_percent = (current / total) * 100
                    status_label.configure(text=f"Status: {progress_percent:.1f}% complete")
                    
                    if eta_label and eta_label.winfo_exists():
                        elapsed = time.time() - app_start_time 
                        eta = calculate_eta(current, total, elapsed)
                        eta_label.configure(text=f"ETA: {eta}")
            else: 
                if current == 0: 
                    if speed_label and speed_label.winfo_exists(): speed_label.configure(text="Speed: Calculating...")
                    if status_label and status_label.winfo_exists(): status_label.configure(text="Status: Preparing...")

        if message and message.strip():
            message_type = "INFO"
            if "SUCCESS" in message.upper() or "found" in message.lower() or "✓" in message:
                message_type = "SUCCESS"
            elif "ERROR" in message.upper() or "failed" in message.lower() or "✗" in message or "aborted" in message.lower():
                message_type = "ERROR"
            elif "WARNING" in message.upper() or "timeout" in message.lower() or "⚠" in message:
                message_type = "WARNING"
            elif any(keyword in message.lower() for keyword in ["detected", "loading", "starting", "◉", "▶"]):
                message_type = "SYSTEM"
            
            should_log_this_message = True
            is_verbose_progress_message = "Trying:" in message or \
                                          "Processing base word:" in message or \
                                          "Trying rule candidate:" in message
            
            if is_verbose_progress_message:
                now_detailed = time.time()
                if (now_detailed - _last_detailed_log_time) < DETAILED_LOG_INTERVAL:
                    should_log_this_message = False
                else:
                    _last_detailed_log_time = now_detailed
            
            if should_log_this_message:
                log_with_timestamp(message.strip(), message_type)
        
     if not root or not root.winfo_exists():
        return

     now = time.time()
    
     is_critical = False
     if not append_message and not message:
        is_critical = True
     elif message and any(keyword in message.lower() for keyword in
                         ["error", "fail", "stop", "found", "success", "starting", 
                          "detected", "aborted", "complete", "unavailable", "✓", "✗", "◉"]):
        is_critical = True
     elif current == 0 and total >= 0:
        is_critical = True
     elif current > 0 and current == total and total > 0:
        is_critical = True

     if is_critical:
        root.after(0, _update_task)
     elif (now - _last_scheduled_ui_update_time) > UI_UPDATE_THROTTLE_INTERVAL:
        _last_scheduled_ui_update_time = now
        root.after(0, _update_task)

    def cracking_task_wrapper():
        global crack_button, stop_button, speed_label, progressbar, root, status_label, eta_label
        try:
            log_with_timestamp("Starting password cracking engine...", "SYSTEM")
            result_tuple = logic.crack_password_main(target_hash, selected_hash_type, attack_mode, attack_params, stop_event_ref, update_ui_from_thread)
            
            found_password = None
            algorithm_actually_used = selected_hash_type

            if result_tuple:
                found_password, algorithm_actually_used = result_tuple

            def _update_ui_post_crack():
                if not root or not root.winfo_exists():
                    return

                if found_password:
                    log_with_timestamp(f"══════════════════════════════════════════════════", "RESULT")
                    log_with_timestamp(f"CRACKING SUCCESSFUL!", "SUCCESS_GLITCH")
                    log_with_timestamp(f">>> Password found: {found_password} <<<", "RESULT")
                    log_with_timestamp(f">>> Algorithm: {algorithm_actually_used} <<<", "RESULT")
                    log_with_timestamp(f"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⠙⠻⢶⣄⡀⠀⠀⠀⢀⣤⠶⠛⠛⡇⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣇⠀⠀⣙⣿⣦⣤⣴⣿⣁⠀⠀⣸⠇⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣡⣾⣿⣿⣿⣿⣿⣿⣿⣷⣌⠋⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣷⣄⡈⢻⣿⡟⢁⣠⣾⣿⣦⠀⠀⠀⠀*grrrr*
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⠘⣿⠃⣿⣿⣿⣿⡏⠀⠀⠀⠀*ihihi*  
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠀⠈⠛⣰⠿⣆⠛⠁⠀⡀⠀⠀⠀⠀⠀ *awoo!*
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⣦⠀⠘⠛⠋⠀⣴⣿⠁⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣀⣤⣶⣾⣿⣿⣿⣿⡇⠀⠀⠀⢸⣿⣏⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣠⣶⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠀⠀⠀⠾⢿⣿⠀⠀⠀⠀⠀⠀
⠀⣠⣿⣿⣿⣿⣿⣿⡿⠟⠋⣁⣠⣤⣤⡶⠶⠶⣤⣄⠈⠀⠀⠀⠀⠀⠀
⢰⣿⣿⣮⣉⣉⣉⣤⣴⣶⣿⣿⣋⡥⠄⠀⠀⠀⠀⠉⢻⣄⠀⠀⠀⠀⠀
⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣟⣋⣁⣤⣀⣀⣤⣤⣤⣤⣄⣿⡄⠀⠀⠀⠀
⠀⠙⠿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠛⠋⠉⠁⠀⠀⠀⠀⠈⠛⠃⠀⠀⠀⠀
⠀⠀⠀⠀⠉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                    """, "RESULT")
                    log_with_timestamp(f"plz donate <3", "RESULT")
                    log_with_timestamp(f"══════════════════════════════════════════════════", "RESULT")
                    
                    if progressbar and progressbar.winfo_exists():
                        progressbar.set(1.0)
                    if status_label and status_label.winfo_exists():
                        status_label.configure(text="Status: Password found!")
                    if speed_label and speed_label.winfo_exists():
                        speed_label.configure(text="Speed: N/A")
                    if eta_label and eta_label.winfo_exists():
                        eta_label.configure(text="ETA: Complete")

                elif stop_event_ref.is_set():
                    log_with_timestamp("Operation stopped by user request", "WARNING")
                    if status_label and status_label.winfo_exists():
                        status_label.configure(text="Status: Stopped by user")
                    if eta_label and eta_label.winfo_exists():
                        eta_label.configure(text="ETA: Cancelled")
                    if speed_label and speed_label.winfo_exists():
                        speed_label.configure(text="Speed: N/A")
                    if progressbar and progressbar.winfo_exists():
                        progressbar.set(1.0)
                else:
                    log_with_timestamp("Password not found with current parameters", "WARNING")
                    log_with_timestamp("Consider trying different attack modes or wordlists", "INFO")
                    if status_label and status_label.winfo_exists():
                        status_label.configure(text="Status: Password not found")
                    if eta_label and eta_label.winfo_exists():
                        eta_label.configure(text="ETA: Failed")
                    if progressbar and progressbar.winfo_exists():
                        progressbar.set(1.0)
                    if speed_label and speed_label.winfo_exists():
                        speed_label.configure(text="Speed: N/A")
                   
            if root and root.winfo_exists():
                root.after(0, _update_ui_post_crack)

        except Exception as e:
            log_with_timestamp(f"Unexpected error in cracking thread: {str(e)}", "ERROR")
            if status_label and status_label.winfo_exists(): status_label.configure(text="Status: Error occurred")
            if eta_label and eta_label.winfo_exists(): eta_label.configure(text="ETA: Error")
            import traceback
            traceback.print_exc()
        finally:
            if root and root.winfo_exists():
                def finalize_ui_on_main_thread():
                    global crack_button, stop_button
                    if crack_button and crack_button.winfo_exists():
                        crack_button.configure(state=tk.NORMAL, text="START CRACK")
                    if stop_button and stop_button.winfo_exists():
                        stop_button.configure(state=tk.DISABLED, text="STOP")
                    stop_pulse_animation()
                root.after(0, finalize_ui_on_main_thread)

    crack_thread = threading.Thread(target=cracking_task_wrapper, daemon=True)
    crack_thread.start()

def on_stop_button_click(stop_event_ref):
    global crack_thread, result_text, stop_button, root
    if crack_thread and crack_thread.is_alive():
        stop_event_ref.set()
        log_with_timestamp("Stop signal sent - waiting for operation to terminate...", "WARNING")
        stop_button.configure(state=tk.DISABLED, text="STOPPING...")
        
        def monitor_thread_termination():
            if crack_thread and crack_thread.is_alive():
                root.after(100, monitor_thread_termination)
            else:
                stop_button.configure(state=tk.DISABLED, text="STOP")
        
        monitor_thread_termination()
    else:
        messagebox.showinfo("No Operation", "No cracking process is currently running.", parent=root)

def setup_probabilistic_options_frame(parent_frame):
    global probabilistic_options_frame, probabilistic_model_path_entry
    global probabilistic_num_candidates_entry, probabilistic_max_len_entry, probabilistic_seed_keyword_entry

    if probabilistic_options_frame is not None and probabilistic_options_frame.winfo_exists():
        return

    probabilistic_options_frame = customtkinter.CTkFrame(parent_frame, 
        fg_color="transparent", 
        border_color=constants.BORDER_COLOR, 
        border_width=2)
    
    prob_header = customtkinter.CTkFrame(probabilistic_options_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    prob_header.pack(fill=tk.X, padx=2, pady=(2,5))
    prob_header.pack_propagate(False)
    customtkinter.CTkLabel(prob_header, text="Probabilistic Configuration (ONNX)", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)

    if not utils.ONNX_HF_AVAILABLE:
        warning_frame = customtkinter.CTkFrame(probabilistic_options_frame, fg_color=constants.ERROR_COLOR)
        warning_frame.pack(fill=tk.X, padx=5, pady=5)
        customtkinter.CTkLabel(warning_frame, 
                              text="⚠ ONNX Runtime & Transformers required for AI mode\nInstall: pip install onnxruntime transformers numpy",
                              text_color=constants.BG_COLOR, 
                              font=constants.FONT_FAMILY_UI).pack(pady=10)
        return

    model_path_frame = customtkinter.CTkFrame(probabilistic_options_frame, fg_color="transparent")
    model_path_frame.pack(fill=tk.X, padx=5, pady=5)
    
    customtkinter.CTkLabel(model_path_frame, text="Model Directory:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, anchor='w', padx=(0,5))
    
    probabilistic_model_path_entry = customtkinter.CTkEntry(model_path_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Select AI model directory...")
    probabilistic_model_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
    
    prob_browse_button = customtkinter.CTkButton(model_path_frame, text="Browse", 
        command=browse_probabilistic_model_path, 
        fg_color=constants.BUTTON_BG_COLOR, 
        hover_color=constants.BUTTON_HOVER_COLOR, 
        text_color=constants.FG_COLOR, 
        font=constants.FONT_FAMILY_BUTTON,
        width=80)
    prob_browse_button.pack(side=tk.RIGHT)
    create_tooltip(prob_browse_button, "Select directory containing AI model files")

    params_frame = customtkinter.CTkFrame(probabilistic_options_frame, fg_color=constants.ENTRY_BG_COLOR)
    params_frame.pack(fill=tk.X, padx=5, pady=5)

    candidates_frame = customtkinter.CTkFrame(params_frame, fg_color="transparent")
    candidates_frame.pack(fill=tk.X, padx=5, pady=5)
    
    customtkinter.CTkLabel(candidates_frame, text="Candidates to Generate:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, padx=(0,5))
    
    probabilistic_num_candidates_entry = customtkinter.CTkEntry(candidates_frame, width=100,
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="100000")
    probabilistic_num_candidates_entry.insert(0, str(constants.DEFAULT_PROBABILISTIC_CANDIDATES))
    probabilistic_num_candidates_entry.pack(side=tk.LEFT, padx=(0,15))
    create_tooltip(probabilistic_num_candidates_entry, "Number of AI-generated password candidates")

    customtkinter.CTkLabel(candidates_frame, text="Max Length:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, padx=(0,5))
    
    probabilistic_max_len_entry = customtkinter.CTkEntry(candidates_frame, width=80,
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="32")
    probabilistic_max_len_entry.insert(0, str(constants.DEFAULT_PROBABILISTIC_MAX_LEN))
    probabilistic_max_len_entry.pack(side=tk.LEFT)
    create_tooltip(probabilistic_max_len_entry, "Maximum length for generated passwords")

    customtkinter.CTkLabel(params_frame, text="Seed Keyword (optional):", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    
    probabilistic_seed_keyword_entry = customtkinter.CTkEntry(params_frame,
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Optional seed word to guide generation...")
    probabilistic_seed_keyword_entry.pack(fill=tk.X, padx=5, pady=(0,5))
    create_tooltip(probabilistic_seed_keyword_entry, "Optional keyword to guide AI password generation")


def setup_rainbow_table_options_frame(parent_frame):
    global rainbow_table_options_frame, rainbow_table_import_wordlist_entry
    global rainbow_table_import_algorithms_var, rainbow_table_export_path_entry, rainbow_table_stats_text

    if rainbow_table_options_frame is not None and rainbow_table_options_frame.winfo_exists():
        rainbow_table_options_frame.pack_forget()

    rainbow_table_options_frame = customtkinter.CTkFrame(parent_frame,
        fg_color="transparent",
        border_color=constants.BORDER_COLOR,
        border_width=0)

    header_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    header_frame.pack(fill=tk.X, padx=2, pady=(2,10))
    header_frame.pack_propagate(False)
    customtkinter.CTkLabel(header_frame, text="Rainbow Table Lookup",
                          text_color=constants.TITLES_COLOR,
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)

    stats_section_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.ENTRY_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    stats_section_frame.pack(fill=tk.X, padx=5, pady=5)

    customtkinter.CTkLabel(stats_section_frame, text="Rainbow Table Statistics",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=10, pady=(5,2))

    rainbow_table_stats_text = tk.Text(stats_section_frame, height=5,
                                      bg=constants.TEXTBOX_BG_COLOR,
                                      fg=constants.FG_COLOR,
                                      font=constants.FONT_FAMILY_MONO,
                                      state=tk.DISABLED,
                                      bd=0, highlightthickness=0, relief=tk.FLAT,
                                      padx=8, pady=5)
    rainbow_table_stats_text.pack(fill=tk.X, padx=10, pady=(0,5))

    refresh_stats_button = customtkinter.CTkButton(stats_section_frame, text="🔄 Refresh Statistics",
        command=refresh_rainbow_table_stats,
        fg_color=constants.BUTTON_BG_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.FG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        height=28)
    refresh_stats_button.pack(pady=(0,10), padx=10, anchor='e')
    create_tooltip(refresh_stats_button, "Reload and display current rainbow table statistics.")

    customtkinter.CTkLabel(rainbow_table_options_frame, text="Table Management Tools",
                          text_color=constants.TITLES_COLOR,
                          font=constants.FONT_FAMILY_HEADER).pack(anchor='w', padx=10, pady=(10,2))

    import_section_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.ENTRY_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    import_section_frame.pack(fill=tk.X, padx=5, pady=5)

    customtkinter.CTkLabel(import_section_frame, text="Import Wordlist to Table",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=10, pady=(5,5))

    import_path_frame = customtkinter.CTkFrame(import_section_frame, fg_color="transparent")
    import_path_frame.pack(fill=tk.X, padx=10, pady=(0,5))

    rainbow_table_import_wordlist_entry = customtkinter.CTkEntry(import_path_frame,
        fg_color=constants.ENTRY_BG_COLOR,
        text_color=constants.FG_COLOR,
        border_color=constants.BORDER_COLOR,
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Select wordlist to import...")
    rainbow_table_import_wordlist_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

    browse_import_button = customtkinter.CTkButton(import_path_frame, text="Browse",
        command=browse_rainbow_import_wordlist,
        fg_color=constants.BUTTON_BG_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.FG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        width=80)
    browse_import_button.pack(side=tk.RIGHT)
    create_tooltip(browse_import_button, "Select a wordlist file to import and hash.")

    algo_frame = customtkinter.CTkFrame(import_section_frame, fg_color="transparent")
    algo_frame.pack(fill=tk.X, padx=10, pady=(0,10))

    customtkinter.CTkLabel(algo_frame, text="Algorithms (comma-separated):",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, padx=(0,10))

    rainbow_table_import_algorithms_var = tk.StringVar(value="MD5,SHA-1,SHA-256")
    algorithms_entry = customtkinter.CTkEntry(algo_frame,
        textvariable=rainbow_table_import_algorithms_var,
        fg_color=constants.ENTRY_BG_COLOR,
        text_color=constants.FG_COLOR,
        border_color=constants.BORDER_COLOR,
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="MD5,SHA-1,SHA-256,...")
    algorithms_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
    create_tooltip(algorithms_entry, "e.g., MD5,SHA-1,SHA-256. bcrypt is not recommended for pre-computation here.")

    import_button = customtkinter.CTkButton(algo_frame, text="Start Import",
        command=import_wordlist_to_rainbow_table,
        fg_color=constants.SUCCESS_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.BG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        width=90)
    import_button.pack(side=tk.RIGHT)
    create_tooltip(import_button, "Begin hashing the wordlist and adding to the rainbow table.")

    export_section_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.ENTRY_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    export_section_frame.pack(fill=tk.X, padx=5, pady=5)

    customtkinter.CTkLabel(export_section_frame, text="Export Rainbow Table",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=10, pady=(5,5))

    export_path_frame = customtkinter.CTkFrame(export_section_frame, fg_color="transparent")
    export_path_frame.pack(fill=tk.X, padx=10, pady=(0,5))

    rainbow_table_export_path_entry = customtkinter.CTkEntry(export_path_frame,
        fg_color=constants.ENTRY_BG_COLOR,
        text_color=constants.FG_COLOR,
        border_color=constants.BORDER_COLOR,
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Export path...")
    rainbow_table_export_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

    browse_export_button = customtkinter.CTkButton(export_path_frame, text="Browse",
        command=browse_rainbow_export_path,
        fg_color=constants.BUTTON_BG_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.FG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        width=80)
    browse_export_button.pack(side=tk.RIGHT, padx=(0,5))
    create_tooltip(browse_export_button, "Choose a location and filename for the export.")

    export_button = customtkinter.CTkButton(export_path_frame, text="Export Now",
        command=export_rainbow_table,
        fg_color=constants.EXPORT_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.BG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        width=90)
    export_button.pack(side=tk.RIGHT)
    create_tooltip(export_button, "Export the rainbow table to a JSON or CSV file.")

    maintenance_section_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.ENTRY_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    maintenance_section_frame.pack(fill=tk.X, padx=5, pady=5)

    customtkinter.CTkLabel(maintenance_section_frame, text="Database Maintenance",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=10, pady=(5,5))

    optimize_button = customtkinter.CTkButton(maintenance_section_frame, text="Optimize Database & Rebuild Bloom Filter",
        command=optimize_rainbow_table_database,
        fg_color=constants.OPTIMIZE_COLOR,
        hover_color=constants.BUTTON_HOVER_COLOR,
        text_color=constants.BG_COLOR,
        font=constants.FONT_FAMILY_BUTTON,
        height=35)
    optimize_button.pack(fill=tk.X, padx=10, pady=(0,10))
    create_tooltip(optimize_button, "Perform database vacuum, reindex, analyze, and rebuild the Bloom filter for optimal performance.")

    info_section_frame = customtkinter.CTkFrame(rainbow_table_options_frame, fg_color=constants.ENTRY_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    info_section_frame.pack(fill=tk.X, padx=5, pady=(10,5))

    customtkinter.CTkLabel(info_section_frame, text="About This Mode",
                          text_color=constants.FG_COLOR,
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=10, pady=(5,2))

    refresh_rainbow_table_stats()

def browse_wordlist_path():
    global wordlist_path_entry, root
    file_path = tkfiledialog.askopenfilename(
        title="Select Wordlist File", 
        filetypes=(("Text files", "*.txt"), ("All files", "*.*")), 
        parent=root
    )
    if file_path: 
        wordlist_path_entry.delete(0, tk.END)
        wordlist_path_entry.insert(0, file_path)

def browse_rule_wordlist_path():
    global rule_wordlist_path_entry, root
    file_path = tkfiledialog.askopenfilename(
        title="Select Wordlist File for Rules", 
        filetypes=(("Text files", "*.txt"), ("All files", "*.*")), 
        parent=root
    )
    if file_path: 
        rule_wordlist_path_entry.delete(0, tk.END)
        rule_wordlist_path_entry.insert(0, file_path)

def browse_probabilistic_model_path():
    global probabilistic_model_path_entry, root
    dir_path = tkfiledialog.askdirectory(title="Select Probabilistic Model Directory", parent=root)
    if dir_path: 
        probabilistic_model_path_entry.delete(0, tk.END)
        probabilistic_model_path_entry.insert(0, dir_path)

def browse_rainbow_import_wordlist():
    global rainbow_table_import_wordlist_entry, root
    file_path = tkfiledialog.askopenfilename(
        title="Select Wordlist to Import", 
        filetypes=(("Text files", "*.txt"), ("All files", "*.*")), 
        parent=root
    )
    if file_path: 
        rainbow_table_import_wordlist_entry.delete(0, tk.END)
        rainbow_table_import_wordlist_entry.insert(0, file_path)

def browse_rainbow_export_path():
    global rainbow_table_export_path_entry, root
    file_path = tkfiledialog.asksaveasfilename(
        title="Export Rainbow Table As", 
        filetypes=(("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")), 
        parent=root
    )
    if file_path: 
        rainbow_table_export_path_entry.delete(0, tk.END)
        rainbow_table_export_path_entry.insert(0, file_path)

def update_attack_mode_options(*args):
    global attack_mode_var, wordlist_options_frame, bruteforce_options_frame, rule_based_options_frame, probabilistic_options_frame, rainbow_table_options_frame, separator_options, root
    mode = attack_mode_var.get()
    
    wordlist_options_frame.pack_forget()
    bruteforce_options_frame.pack_forget()
    rule_based_options_frame.pack_forget()
    if probabilistic_options_frame and probabilistic_options_frame.winfo_exists():
        probabilistic_options_frame.pack_forget()
    if rainbow_table_options_frame and rainbow_table_options_frame.winfo_exists():
        rainbow_table_options_frame.pack_forget()

    if mode == "Wordlist":
        wordlist_options_frame.pack(fill=tk.X, pady=5, padx=5, before=separator_options)
    elif mode == "Brute-Force":
        bruteforce_options_frame.pack(fill=tk.X, pady=5, padx=5, before=separator_options)
    elif mode == "Rule-Based":
        rule_based_options_frame.pack(fill=tk.X, pady=5, padx=5, before=separator_options)
    elif mode == "Probabilistic":
        if not (probabilistic_options_frame and probabilistic_options_frame.winfo_exists()):
            setup_probabilistic_options_frame(main_app_frame_ref)
        if probabilistic_options_frame and probabilistic_options_frame.winfo_exists():
            if utils.ONNX_HF_AVAILABLE:
                probabilistic_options_frame.pack(fill=tk.X, pady=5, padx=5, before=separator_options)
            else:
                log_with_timestamp("Probabilistic mode requires ONNX Runtime and Transformers", "WARNING")
    elif mode == "Rainbow Table":
        if not (rainbow_table_options_frame and rainbow_table_options_frame.winfo_exists()):
            setup_rainbow_table_options_frame(main_app_frame_ref)
        if rainbow_table_options_frame and rainbow_table_options_frame.winfo_exists():
            rainbow_table_options_frame.pack(fill=tk.X, pady=5, padx=5, before=separator_options)

def refresh_rainbow_table_stats():
    global rainbow_table_stats_text
    
    if not rainbow_table_stats_text or not rainbow_table_stats_text.winfo_exists():
        return
    
    try:
        manager = rainbow_tables.get_rainbow_manager()
        stats = manager.get_statistics()
        
        stats_text = []
        stats_text.append(f"Total Hashes: {stats['total_hashes']:,}")
        stats_text.append(f"Cache Hit Ratio: {stats.get('cache_hit_ratio', 0):.2%}")
        stats_text.append(f"Bloom Filter Efficiency: {stats.get('bloom_hit_ratio', 0):.2%}")
        stats_text.append(f"Successful Lookups: {stats['successful_lookups']:,}")
        
        if 'algorithm_stats' in stats:
            stats_text.append("\nPer Algorithm:")
            for algo, algo_stats in stats['algorithm_stats'].items():
                stats_text.append(f"  • {algo}: {algo_stats['count']:,} hashes")
        
        rainbow_table_stats_text.configure(state="normal")
        rainbow_table_stats_text.delete("1.0", tk.END)
        rainbow_table_stats_text.insert("1.0", "\n".join(stats_text))
        rainbow_table_stats_text.configure(state="disabled")
        
    except Exception as e:
        rainbow_table_stats_text.configure(state="normal")
        rainbow_table_stats_text.delete("1.0", tk.END)
        rainbow_table_stats_text.insert("1.0", f"Error loading stats: {str(e)}")
        rainbow_table_stats_text.configure(state="disabled")

def import_wordlist_to_rainbow_table():
    global rainbow_table_import_wordlist_entry, rainbow_table_import_algorithms_var
    
    wordlist_path = rainbow_table_import_wordlist_entry.get().strip()
    algorithms_str = rainbow_table_import_algorithms_var.get().strip()
    
    if not wordlist_path or not os.path.exists(wordlist_path):
        messagebox.showerror("Error", "Please select a valid wordlist file.", parent=root)
        return
    
    if not algorithms_str:
        messagebox.showerror("Error", "Please specify algorithms to generate.", parent=root)
        return
    
    algorithms = [algo.strip() for algo in algorithms_str.split(',')]
    
    valid_algorithms = []
    for algo in algorithms:
        if algo in constants.HASH_ALGORITHMS:
            valid_algorithms.append(algo)
        else:
            messagebox.showwarning("Warning", f"Unknown algorithm '{algo}' will be skipped.", parent=root)
    
    if not valid_algorithms:
        messagebox.showerror("Error", "No valid algorithms specified.", parent=root)
        return
    
    def import_task():
        try:
            manager = rainbow_tables.get_rainbow_manager()
            
            def progress_update(current, total, message, append, speed):
                log_with_timestamp(f"Import progress: {current}/{total} - {message}", "INFO")
            
            success = manager.import_wordlist_as_rainbow_table(wordlist_path, valid_algorithms, progress_update)
            
            if success:
                log_with_timestamp(f"Successfully imported wordlist with {len(valid_algorithms)} algorithms", "SUCCESS")
                root.after(0, refresh_rainbow_table_stats)
            else:
                log_with_timestamp("Failed to import wordlist", "ERROR")
                
        except Exception as e:
            log_with_timestamp(f"Import error: {str(e)}", "ERROR")
    
    import_thread = threading.Thread(target=import_task, daemon=True)
    import_thread.start()
    
    log_with_timestamp(f"Starting import of {wordlist_path} with algorithms: {', '.join(valid_algorithms)}", "INFO")

def export_rainbow_table():
    global rainbow_table_export_path_entry
    
    export_path = rainbow_table_export_path_entry.get().strip()
    
    if not export_path:
        messagebox.showerror("Error", "Please specify export path.", parent=root)
        return
    
    try:
        manager = rainbow_tables.get_rainbow_manager()
        
        format_type = 'json'
        if export_path.lower().endswith('.csv'):
            format_type = 'csv'
        
        manager.export_rainbow_table(export_path, format=format_type)
        log_with_timestamp(f"Rainbow table exported to {export_path}", "SUCCESS")
        messagebox.showinfo("Success", f"Rainbow table exported successfully to:\n{export_path}", parent=root)
        
    except Exception as e:
        log_with_timestamp(f"Export error: {str(e)}", "ERROR")
        messagebox.showerror("Error", f"Failed to export rainbow table:\n{str(e)}", parent=root)

def optimize_rainbow_table_database():
    try:
        log_with_timestamp("Starting database optimization...", "INFO")
        manager = rainbow_tables.get_rainbow_manager()
        manager.optimize_database()
        log_with_timestamp("Database optimization completed", "SUCCESS")
        refresh_rainbow_table_stats()
        messagebox.showinfo("Success", "Database optimization completed successfully!", parent=root)
        
    except Exception as e:
        log_with_timestamp(f"Optimization error: {str(e)}", "ERROR")
        messagebox.showerror("Error", f"Failed to optimize database:\n{str(e)}", parent=root)

def create_gui(stop_event_ref):
    global root, target_hash_entry, hash_type_combo, attack_mode_var, wordlist_options_frame, bruteforce_options_frame, rule_based_options_frame
    global wordlist_path_entry, max_wordlist_length_entry, charset_entry, bf_min_len_entry, bf_max_len_entry
    global rule_wordlist_path_entry, max_candidate_length_entry, rule_capitalize_var, rule_append_numbers_var, rule_leet_speak_var, rule_toggle_case_var, rule_reverse_word_var, rule_prepend_append_common_var
    global result_text, progressbar, speed_label, crack_button, stop_button, separator_options, main_app_frame_ref, status_label, eta_label
    global save_to_rainbow_table_var

    customtkinter.set_appearance_mode("Dark")
    root = customtkinter.CTk()
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        if platform.system() == "Windows":
            ico_path = os.path.join(base_path, "assets/p0.ico")
            if os.path.exists(ico_path):
                root.iconbitmap(ico_path)
            else:
                print(f"Warning: Icon file 'p0.ico' not found at {ico_path}")
        else:
            png_path = os.path.join(base_path, "assets/p0.png")
            if os.path.exists(png_path):
                root.icon_image = tk.PhotoImage(file=png_path)
                root.iconphoto(True, root.icon_image)
            else:
                print(f"Warning: Icon file 'p0.png' not found at {png_path}")
    except Exception as e:
        print(f"Error setting application icon: {e}")

    root.overrideredirect(True)
    root.geometry("1350x800") 
    root.resizable(True, True)
    root.configure(fg_color=constants.BG_COLOR)

    title_bar_frame = tk.Frame(root, bg=constants.BG_COLOR, relief='flat', bd=0, 
                              highlightthickness=0)
    title_bar_frame.pack(side=tk.TOP, fill=tk.X)
    
    TITLE_BAR_LOGO_FILENAME = "assets/p0-border.png"
    try:
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), TITLE_BAR_LOGO_FILENAME)
        if os.path.exists(logo_path):
            title_bar_logo_image = customtkinter.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(20, 20)
            )
            title_bar_logo_label = customtkinter.CTkLabel(
                title_bar_frame,
                image=title_bar_logo_image,
                text="",
                fg_color="transparent"
            )
            title_bar_logo_label.pack(side=tk.LEFT, padx=(15, 5), pady=7)
            title_bar_logo_label.bind("<ButtonPress-1>", on_title_bar_press)
            title_bar_logo_label.bind("<B1-Motion>", on_title_bar_drag)
        else:
            print(f"Warning: Title bar logo '{TITLE_BAR_LOGO_FILENAME}' not found.")
    except Exception as e:
        print(f"Error loading title bar logo: {e}")

    title_label = tk.Label(title_bar_frame, text="Polycrypt Zero", 
                          bg=constants.BG_COLOR, fg=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_TITLE)
    title_label.pack(side=tk.LEFT, padx=(0, 10), pady=8) 

    GITHUB_URL = "https://github.com/bitArtisan1/p0-Decryption-Tool"
    GITHUB_ICON_FILENAME = "assets/github-icon.png"
    try:
        github_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), GITHUB_ICON_FILENAME)
        if os.path.exists(github_icon_path):
            github_image = customtkinter.CTkImage(
                light_image=Image.open(github_icon_path),
                dark_image=Image.open(github_icon_path),
                size=(20, 20)
            )
            github_button = customtkinter.CTkButton(
                title_bar_frame,
                image=github_image,
                text="",
                command=lambda: webbrowser.open_new_tab(GITHUB_URL),
                width=28,
                height=28,
                fg_color=constants.BUTTON_BG_COLOR,
                hover_color=constants.BUTTON_HOVER_COLOR,
                corner_radius=3,
                border_width=1,
                border_color=constants.BORDER_COLOR
            )
            github_button.pack(side=tk.LEFT, padx=(0, 5), pady=6)
            create_tooltip(github_button, "View Source Code on GitHub")
        else:
            print(f"Warning: GitHub icon '{GITHUB_ICON_FILENAME}' not found.")
    except Exception as e:
        print(f"Error loading GitHub icon: {e}")

    KOFI_URL = "https://ko-fi.com/bitArtisan1"
    DONATE_ICON_FILENAME = "assets/dollar-icon.png"
    try:
        donate_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DONATE_ICON_FILENAME)
        if os.path.exists(donate_icon_path):
            donate_image = customtkinter.CTkImage(
                light_image=Image.open(donate_icon_path),
                dark_image=Image.open(donate_icon_path),
                size=(18, 18)
            )
            donate_button = customtkinter.CTkButton(
                title_bar_frame,
                image=donate_image,
                text="",
                command=lambda: webbrowser.open_new_tab(KOFI_URL),
                width=28,
                height=28,
                fg_color=constants.SUCCESS_COLOR,
                hover_color=constants.EXPORT_COLOR,
                text_color=constants.BG_COLOR,
                corner_radius=3,
                border_width=1,
                border_color=constants.BORDER_COLOR
            )
            donate_button.pack(side=tk.LEFT, padx=(0, 10), pady=6)
            create_tooltip(donate_button, "If you like this tool, support me by buying a coffee! 🤍")

            donate_button.original_border_color = donate_button._border_color 
            donate_button.pulse_colors = [constants.TITLES_COLOR, constants.SUCCESS_COLOR] 
            donate_button.current_pulse_index = 0
            donate_button.hover_animation_id = None
            donate_button.is_hovering_for_animation = False

            def _animate_donate_border_pulse():
                if not donate_button.winfo_exists() or not donate_button.is_hovering_for_animation:
                    if hasattr(donate_button, 'hover_animation_id') and donate_button.hover_animation_id:
                        donate_button.after_cancel(donate_button.hover_animation_id)
                        donate_button.hover_animation_id = None
                    if hasattr(donate_button, 'original_border_color') and donate_button.original_border_color is not None:
                        donate_button.configure(border_color=donate_button.original_border_color)
                    return

                donate_button.current_pulse_index = (donate_button.current_pulse_index + 1) % len(donate_button.pulse_colors)
                new_border_color = donate_button.pulse_colors[donate_button.current_pulse_index]
                donate_button.configure(border_color=new_border_color)
                
                donate_button.hover_animation_id = donate_button.after(1000, _animate_donate_border_pulse)

            def on_donate_button_enter(event):
                donate_button.is_hovering_for_animation = True
                if not hasattr(donate_button, 'original_border_color') or donate_button.original_border_color is None:
                    donate_button.original_border_color = donate_button._border_color 
                donate_button.current_pulse_index = 0 
                _animate_donate_border_pulse()

            def on_donate_button_leave(event):
                donate_button.is_hovering_for_animation = False

            donate_button.bind("<Enter>", on_donate_button_enter, add="+")
            donate_button.bind("<Leave>", on_donate_button_leave, add="+")

        else:
            print(f"Warning: Donate icon '{DONATE_ICON_FILENAME}' not found.")
    except Exception as e:
        print(f"Error loading donate icon: {e}")
    
    close_button = tk.Button(title_bar_frame, text="✕", command=root.destroy, 
                            bg=constants.BG_COLOR, fg=constants.ERROR_COLOR, 
                            activebackground=constants.ERROR_COLOR, activeforeground=constants.BG_COLOR, 
                            relief='flat', font=("Segoe UI", 10, "bold"), 
                            bd=0, highlightthickness=0, padx=8, pady=4)
    close_button.pack(side=tk.RIGHT, padx=(0,8), pady=8)
    
    minimize_button = tk.Button(title_bar_frame, text="−", command=minimize_window, 
                               bg=constants.BG_COLOR, fg=constants.TITLES_COLOR, 
                               activebackground=constants.BUTTON_HOVER_COLOR, activeforeground=constants.TITLES_COLOR, 
                               relief='flat', font=("Segoe UI", 10, "bold"), 
                               bd=0, highlightthickness=0, padx=8, pady=4)
    minimize_button.pack(side=tk.RIGHT, padx=(0,0), pady=8)
    
    root.bind("<Map>", on_deiconify)
    root.bind("<FocusIn>", on_deiconify)
    title_bar_frame.bind("<ButtonPress-1>", on_title_bar_press)
    title_bar_frame.bind("<B1-Motion>", on_title_bar_drag)
    title_label.bind("<ButtonPress-1>", on_title_bar_press)
    title_label.bind("<B1-Motion>", on_title_bar_drag)

    main_content_container = customtkinter.CTkFrame(root, fg_color=constants.BG_COLOR)
    main_content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))

    paned_window = tk.PanedWindow(main_content_container, 
                                  orient=tk.HORIZONTAL, 
                                  sashrelief=tk.FLAT,
                                  bg=constants.BG_COLOR, 
                                  bd=0, 
                                  sashwidth=1)
    paned_window.pack(fill=tk.BOTH, expand=True)

    left_panel_base = customtkinter.CTkFrame(paned_window, fg_color=constants.BG_COLOR) 
    left_panel_scrollable_frame = customtkinter.CTkScrollableFrame(left_panel_base, fg_color=constants.BG_COLOR, scrollbar_button_color=constants.SCROLLBAR_BUTTON_COLOR)
    left_panel_scrollable_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    main_app_frame_ref = left_panel_scrollable_frame 
    paned_window.add(left_panel_base, width=850) 

    right_panel_frame = customtkinter.CTkFrame(paned_window, fg_color=constants.BG_COLOR)
    paned_window.add(right_panel_frame, minsize=200) 

    settings_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    settings_frame.pack(fill=tk.X, pady=5, padx=5)
    
    settings_header = customtkinter.CTkFrame(settings_frame, fg_color=constants.BUTTON_BG_COLOR, height=35)
    settings_header.pack(fill=tk.X, padx=2, pady=(2,5))
    settings_header.pack_propagate(False)
    customtkinter.CTkLabel(settings_header, text="Target Configuration", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=7)

    customtkinter.CTkLabel(settings_frame, text="Target Hash:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    target_hash_entry = customtkinter.CTkEntry(settings_frame, width=70, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Enter hash to crack...")
    target_hash_entry.pack(fill=tk.X, padx=5, pady=(0,8))
    create_tooltip(target_hash_entry, "Paste the hash you want to crack here")

    customtkinter.CTkLabel(settings_frame, text="Hash Algorithm:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    hash_type_combo = customtkinter.CTkComboBox(settings_frame, width=68, 
        values=constants.ALL_HASH_TYPES, state="readonly", 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        button_color=constants.BUTTON_BG_COLOR, 
        button_hover_color=constants.BUTTON_HOVER_COLOR, 
        dropdown_fg_color=constants.ENTRY_BG_COLOR, 
        dropdown_text_color=constants.FG_COLOR, 
        dropdown_hover_color=constants.BUTTON_HOVER_COLOR, 
        font=constants.FONT_FAMILY_UI)
    hash_type_combo.set("Auto-Detect")
    hash_type_combo.pack(fill=tk.X, padx=5, pady=(0,5))
    create_tooltip(hash_type_combo, "Select hash algorithm or use auto-detection")

    save_to_rainbow_table_var = tk.BooleanVar(value=False)
    save_to_rainbow_checkbox = customtkinter.CTkCheckBox(settings_frame,
                                                         text="Automatically add found passwords to Rainbow Table",
                                                         variable=save_to_rainbow_table_var,
                                                         onvalue=True, offvalue=False,
                                                         text_color=constants.FG_COLOR,
                                                         font=constants.FONT_FAMILY_UI,
                                                         fg_color=constants.BUTTON_BG_COLOR, 
                                                         hover_color=constants.BUTTON_HOVER_COLOR,
                                                         checkbox_width=18, checkbox_height=18,
                                                         checkmark_color=constants.SUCCESS_COLOR,
                                                         corner_radius=5)
    save_to_rainbow_checkbox.pack(anchor='w', padx=5, pady=(5, 8))
    create_tooltip(save_to_rainbow_checkbox, "If checked:\n- For non-bcrypt hashes: ALL processed password-hash pairs from attacks will be added.\n- For bcrypt hashes: Only successfully cracked passwords will be added.\nIf unchecked, NO hashes will be added from any attack mode.")

    attack_mode_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    attack_mode_frame.pack(fill=tk.X, pady=5, padx=5)
    
    attack_header = customtkinter.CTkFrame(attack_mode_frame, fg_color=constants.BUTTON_BG_COLOR, height=35)
    attack_header.pack(fill=tk.X, padx=2, pady=(2,5))
    attack_header.pack_propagate(False)
    customtkinter.CTkLabel(attack_header, text="Attack Strategy", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=7)

    attack_mode_var = tk.StringVar(value="Wordlist")
    attack_mode_var.trace_add("write", update_attack_mode_options)

    mode_buttons_frame = customtkinter.CTkFrame(attack_mode_frame, fg_color="transparent")
    mode_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

    modes = [
        ("Wordlist", "Wordlist", "Dictionary-based attack using common passwords"),
        ("Brute-Force", "Brute-Force", "Systematic testing of all possible combinations"),
        ("Rule-Based", "Rule-Based", "Transform wordlist entries using common patterns"),
        ("Probabilistic", "Probabilistic", "AI-powered password generation"),
        ("Rainbow Table", "Rainbow Table", "Lightning-fast precomputed hash lookup")
    ]

    for i, (display_text, value, tooltip) in enumerate(modes):
        btn = tk.Radiobutton(mode_buttons_frame, text=display_text, variable=attack_mode_var, value=value, 
                            font=constants.FONT_FAMILY_UI, fg=constants.FG_COLOR, bg=constants.BG_COLOR, 
                            selectcolor=constants.BG_COLOR, activebackground=constants.BUTTON_HOVER_COLOR, 
                            activeforeground=constants.FG_COLOR, indicatoron=1, highlightthickness=0, 
                            bd=0, anchor='w', padx=8)
        btn.pack(side=tk.LEFT, padx=10, pady=8, fill=tk.X, expand=True)
        create_tooltip(btn, tooltip)

    separator_options = customtkinter.CTkFrame(left_panel_scrollable_frame, height=0, fg_color="transparent")
    separator_options.pack()

    wordlist_options_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    wordlist_header = customtkinter.CTkFrame(wordlist_options_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    wordlist_header.pack(fill=tk.X, padx=2, pady=(2,5))
    wordlist_header.pack_propagate(False)
    customtkinter.CTkLabel(wordlist_header, text="Wordlist Configuration", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)
    wordlist_path_frame = customtkinter.CTkFrame(wordlist_options_frame, fg_color="transparent")
    wordlist_path_frame.pack(fill=tk.X, padx=5, pady=5)
    customtkinter.CTkLabel(wordlist_path_frame, text="Wordlist File:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, anchor='w', padx=(0,5))
    wordlist_path_entry = customtkinter.CTkEntry(wordlist_path_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Select wordlist file...")
    wordlist_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
    browse_button = customtkinter.CTkButton(wordlist_path_frame, text="Browse", 
        command=browse_wordlist_path, 
        fg_color=constants.BUTTON_BG_COLOR, 
        hover_color=constants.BUTTON_HOVER_COLOR, 
        text_color=constants.FG_COLOR, 
        font=constants.FONT_FAMILY_BUTTON)
    browse_button.pack(side=tk.RIGHT, padx=(5,0))
    create_tooltip(browse_button, "Select a wordlist file containing potential passwords")
    customtkinter.CTkLabel(wordlist_options_frame, text="Maximum Password Length (0 = no limit):", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    max_wordlist_length_entry = customtkinter.CTkEntry(wordlist_options_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="0")
    max_wordlist_length_entry.insert(0, "0")
    max_wordlist_length_entry.pack(fill=tk.X, padx=5, pady=(0,8))
    create_tooltip(max_wordlist_length_entry, "Filter wordlist by maximum password length")

    bruteforce_options_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    bf_header = customtkinter.CTkFrame(bruteforce_options_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    bf_header.pack(fill=tk.X, padx=2, pady=(2,5))
    bf_header.pack_propagate(False)
    customtkinter.CTkLabel(bf_header, text="Brute-Force Configuration", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)
    customtkinter.CTkLabel(bruteforce_options_frame, text="Character Set:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    charset_entry = customtkinter.CTkEntry(bruteforce_options_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO)
    charset_entry.insert(0, constants.DEFAULT_CHARSET)
    charset_entry.pack(fill=tk.X, padx=5, pady=(0,5))
    create_tooltip(charset_entry, "Characters to use in brute-force attack")
    bf_len_frame = customtkinter.CTkFrame(bruteforce_options_frame, fg_color="transparent")
    bf_len_frame.pack(fill=tk.X, padx=5, pady=5)
    customtkinter.CTkLabel(bf_len_frame, text="Minimum Length:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, padx=(0,5))
    bf_min_len_entry = customtkinter.CTkEntry(bf_len_frame, width=80, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO)
    bf_min_len_entry.insert(0, "1")
    bf_min_len_entry.pack(side=tk.LEFT, padx=(0,15))
    customtkinter.CTkLabel(bf_len_frame, text="Maximum Length:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, padx=(0,5))
    bf_max_len_entry = customtkinter.CTkEntry(bf_len_frame, width=80, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO)
    bf_max_len_entry.insert(0, "8")
    bf_max_len_entry.pack(side=tk.LEFT)

    rule_based_options_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    rule_header = customtkinter.CTkFrame(rule_based_options_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    rule_header.pack(fill=tk.X, padx=2, pady=(2,5))
    rule_header.pack_propagate(False)
    customtkinter.CTkLabel(rule_header, text="Rule-Based Configuration", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)
    rule_wordlist_path_frame = customtkinter.CTkFrame(rule_based_options_frame, fg_color="transparent")
    rule_wordlist_path_frame.pack(fill=tk.X, padx=5, pady=5)
    customtkinter.CTkLabel(rule_wordlist_path_frame, text="Base Wordlist:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(side=tk.LEFT, anchor='w', padx=(0,5))
    rule_wordlist_path_entry = customtkinter.CTkEntry(rule_wordlist_path_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="Select base wordlist...")
    rule_wordlist_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
    rule_browse_button = customtkinter.CTkButton(rule_wordlist_path_frame, text="Browse", 
        command=browse_rule_wordlist_path, 
        fg_color=constants.BUTTON_BG_COLOR, 
        hover_color=constants.BUTTON_HOVER_COLOR, 
        text_color=constants.FG_COLOR, 
        font=constants.FONT_FAMILY_BUTTON)
    rule_browse_button.pack(side=tk.RIGHT, padx=(5,0))
    customtkinter.CTkLabel(rule_based_options_frame, text="Maximum Candidate Length (0 = no limit):", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,0))
    max_candidate_length_entry = customtkinter.CTkEntry(rule_based_options_frame, 
        fg_color=constants.ENTRY_BG_COLOR, 
        text_color=constants.FG_COLOR, 
        border_color=constants.BORDER_COLOR, 
        font=constants.FONT_FAMILY_MONO,
        placeholder_text="0")
    max_candidate_length_entry.insert(0, "0")
    max_candidate_length_entry.pack(fill=tk.X, padx=5, pady=(0,5))
    rules_selection_frame = customtkinter.CTkFrame(rule_based_options_frame, fg_color="transparent")
    rules_selection_frame.pack(fill=tk.X, padx=5, pady=5)
    customtkinter.CTkLabel(rules_selection_frame, text="Transformation Rules:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', pady=(5,8))
    rule_capitalize_var = tk.BooleanVar(value=True)
    rule_append_numbers_var = tk.BooleanVar(value=True)
    rule_leet_speak_var = tk.BooleanVar(value=False)
    rule_toggle_case_var = tk.BooleanVar(value=False)
    rule_reverse_word_var = tk.BooleanVar(value=False)
    rule_prepend_append_common_var = tk.BooleanVar(value=False)
    rules = [
        (rule_capitalize_var, "Capitalize First Letter", "password → Password"),
        (rule_append_numbers_var, "Append Numbers/Symbols", "password → password123!"),
        (rule_leet_speak_var, "Leetspeak Transform", "password → p@ssw0rd"),
        (rule_toggle_case_var, "Toggle Case", "password → pASSWORD"),
        (rule_reverse_word_var, "↩Reverse Word", "password → drowssap"),
        (rule_prepend_append_common_var, "Add Common Pre/Suffixes", "password → adminpassword123")
    ]
    for var, text, tooltip in rules:
        cb = customtkinter.CTkCheckBox(rules_selection_frame, text=text, variable=var, 
                                      text_color=constants.FG_COLOR, 
                                      font=constants.FONT_FAMILY_UI, 
                                      hover_color=constants.BUTTON_HOVER_COLOR, 
                                      fg_color=constants.BUTTON_BG_COLOR, 
                                      checkmark_color=constants.SUCCESS_COLOR)
        cb.pack(anchor='w', padx=10, pady=2)
        create_tooltip(cb, tooltip)

    setup_probabilistic_options_frame(left_panel_scrollable_frame)
    setup_rainbow_table_options_frame(left_panel_scrollable_frame)

    controls_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent")
    controls_frame.pack(fill=tk.X, pady=15, padx=5)
    crack_button = customtkinter.CTkButton(controls_frame, text="START CRACK", 
        command=lambda: on_crack_button_click(stop_event_ref), 
        fg_color=constants.BUTTON_BG_COLOR, 
        hover_color=constants.SUCCESS_COLOR, 
        text_color=constants.FG_COLOR, 
        font=constants.FONT_FAMILY_BUTTON,
        height=40,
        border_width=2,
        border_color=constants.SUCCESS_COLOR)
    crack_button.pack(side=tk.LEFT, expand=True, padx=(0,5), fill=tk.X)
    stop_button = customtkinter.CTkButton(controls_frame, text="STOP", 
        command=lambda: on_stop_button_click(stop_event_ref), 
        state=tk.DISABLED, 
        fg_color=constants.BUTTON_BG_COLOR, 
        hover_color=constants.ERROR_COLOR, 
        text_color=constants.ERROR_COLOR, 
        font=constants.FONT_FAMILY_BUTTON,
        height=40,
        border_width=2,
        border_color=constants.ERROR_COLOR)
    stop_button.pack(side=tk.RIGHT, expand=True, padx=(5,0), fill=tk.X)

    def add_button_hover_effect(button, normal_text_color, hover_text_color):
        def on_enter(e):
            button.configure(text_color=hover_text_color)
        def on_leave(e):
            button.configure(text_color=normal_text_color)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    add_button_hover_effect(crack_button, constants.FG_COLOR, constants.TITLES_COLOR)
    add_button_hover_effect(stop_button, constants.ERROR_COLOR, constants.TITLES_COLOR)

    status_frame = customtkinter.CTkFrame(left_panel_scrollable_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    status_frame.pack(fill=tk.X, pady=5, padx=5)
    status_header = customtkinter.CTkFrame(status_frame, fg_color=constants.BUTTON_BG_COLOR, height=30)
    status_header.pack(fill=tk.X, padx=2, pady=(2,5))
    status_header.pack_propagate(False)
    customtkinter.CTkLabel(status_header, text="Operation Status", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)
    customtkinter.CTkLabel(status_frame, text="Progress:", 
                          text_color=constants.FG_COLOR, 
                          font=constants.FONT_FAMILY_UI).pack(anchor='w', padx=5, pady=(5,2))
    progressbar = customtkinter.CTkProgressBar(status_frame, orientation="horizontal", 
        progress_color=constants.PROGRESS_BAR_COLOR, 
        fg_color=constants.PROGRESS_TROUGH_COLOR,
        height=20,
        border_width=1,
        border_color=constants.BORDER_COLOR)
    progressbar.set(0)
    progressbar.pack(fill=tk.X, padx=5, pady=(0,8))
    status_info_frame = customtkinter.CTkFrame(status_frame, fg_color="transparent")
    status_info_frame.pack(fill=tk.X, padx=5, pady=(0,8))
    status_label = customtkinter.CTkLabel(status_info_frame, text="Status: Ready", 
                                         text_color=constants.FG_COLOR, 
                                         font=constants.FONT_FAMILY_UI)
    status_label.pack(side=tk.LEFT, anchor='w')
    speed_label = customtkinter.CTkLabel(status_info_frame, text="Speed: N/A", 
                                        text_color=constants.FG_COLOR, 
                                        font=constants.FONT_FAMILY_UI)
    speed_label.pack(side=tk.LEFT, anchor='w', padx=(20,0))
    eta_label = customtkinter.CTkLabel(status_info_frame, text="ETA: N/A", 
                                      text_color=constants.FG_COLOR, 
                                      font=constants.FONT_FAMILY_UI)
    eta_label.pack(side=tk.RIGHT, anchor='e')


    output_frame_container = customtkinter.CTkFrame(right_panel_frame, fg_color="transparent", border_color=constants.BORDER_COLOR, border_width=2)
    output_frame_container.pack(fill=tk.BOTH, expand=True, pady=5, padx=0) 

    output_header = customtkinter.CTkFrame(output_frame_container, fg_color=constants.BUTTON_BG_COLOR, height=30)
    output_header.pack(fill=tk.X, padx=2, pady=(2,0))
    output_header.pack_propagate(False)
    customtkinter.CTkLabel(output_header, text="Operation Log", 
                          text_color=constants.TITLES_COLOR, 
                          font=constants.FONT_FAMILY_HEADER).pack(pady=5)

    log_container = customtkinter.CTkFrame(output_frame_container, fg_color=constants.TEXTBOX_BG_COLOR, border_width=1, border_color=constants.BORDER_COLOR)
    log_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0,2))

    result_text = tk.Text(log_container, 
                         bg=constants.TEXTBOX_BG_COLOR, 
                         fg=constants.FG_COLOR, 
                         font=constants.FONT_FAMILY_LOG,
                         wrap=tk.WORD, 
                         state=tk.DISABLED,
                         bd=0,
                         highlightthickness=0,
                         selectbackground=constants.BUTTON_HOVER_COLOR,
                         selectforeground=constants.FG_COLOR,
                         insertbackground=constants.FG_COLOR,
                         padx=12,
                         pady=8)
    
    log_scrollbar = customtkinter.CTkScrollbar(log_container, 
                                              orientation="vertical",
                                              command=result_text.yview,
                                              fg_color=constants.SCROLLBAR_BUTTON_COLOR,
                                              button_color=constants.SCROLLBAR_BUTTON_HOVER_COLOR,
                                              button_hover_color=constants.TITLES_COLOR)
    
    result_text.configure(yscrollcommand=log_scrollbar.set)
    result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    update_attack_mode_options()
    
    def show_welcome_message():
        welcome_lines = [
            "══════════════════════════════════════════════════",
            """
            ┏┓  ┓            ┏┓                 
            ┃┃┏┓┃┓┏┏┏┓┓┏┏┓╋  ┏┛┏┓┏┓┏┓          
            ┣┛┗┛┗┗┫┗┛ ┗┫┣┛┗  ┗┛┗ ┛ ┗┛
                  ┛    ┛┛      
               Hash Decryption Tool
                  by bitArtisan1      
            """,
            "══════════════════════════════════════════════════",
            "",
            "▶ Hash Algorithms Supported: " + str(len(constants.HASH_ALGORITHMS) + 1),
            "▶ AI-Probablistic Generation: " + ("Available" if utils.ONNX_HF_AVAILABLE else "Unavailable"),
            "",
            "⚠ Configure your attack parameters and target hash",
            "",
            "══════════════════════════════════════════════════",
            """
   ,  ,  , , ,      
  <(__)> | | |      
  | \/ | \_|_/      This tool is for educational
  \^  ^/   |        purposes only, please use
  /\--/\  /|        with caution. ^_^
 /  \/  \/ |                                                
            """

        ]
        
        result_text.configure(state="normal")
        for line in welcome_lines:
            result_text.insert(tk.END, line + "\n")
        result_text.see(tk.END)
        result_text.configure(state="disabled")
    
    root.after(500, show_welcome_message)

    footer_frame = customtkinter.CTkFrame(root, fg_color=constants.BUTTON_BG_COLOR, height=25)
    footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=10) 
    footer_frame.pack_propagate(False)
    
    system_info = f"System: {platform.system()} | Python: {platform.python_version()} | ONNX: {'✓' if utils.ONNX_HF_AVAILABLE else '✗'} | Version: 0.8.0"
    footer_label = customtkinter.CTkLabel(footer_frame, text=system_info, 
                                         text_color=constants.DISABLED_FG_COLOR, 
                                         font=("Consolas", 8))
    footer_label.pack(pady=4)

    def on_key_press(event):
        if event.state & 0x4:
            if event.keysym.lower() == 'return':
                if crack_button.cget("state") != tk.DISABLED:
                    on_crack_button_click(stop_event_ref)
            elif event.keysym.lower() == 'q':
                root.destroy()
            elif event.keysym.lower() == 's':
                if stop_button.cget("state") != tk.DISABLED:
                    on_stop_button_click(stop_event_ref)

    root.bind("<KeyPress>", on_key_press)
    root.focus_set()

    close_button.bind("<Enter>", lambda e: close_button.configure(bg=constants.DARK_RED_HOVER_COLOR))
    close_button.bind("<Leave>", lambda e: close_button.configure(bg=constants.BG_COLOR))
    
    minimize_button.bind("<Enter>", lambda e: minimize_button.configure(bg=constants.BUTTON_HOVER_COLOR))
    minimize_button.bind("<Leave>", lambda e: minimize_button.configure(bg=constants.BG_COLOR))

    def fade_in_animation(alpha=0.0):
        if alpha < 1.0:
            root.attributes('-alpha', alpha)
            root.after(20, lambda: fade_in_animation(alpha + 0.05))
        else:
            root.attributes('-alpha', 1.0)

    root.attributes('-alpha', 0.0)
    root.after(100, fade_in_animation)

    def create_glow_effect(widget):
        original_border_color = widget.cget("border_color")
        
        def pulse_glow(increasing=True, intensity=0):
            if not widget.winfo_exists():
                return
            
            if increasing:
                intensity += 5
                if intensity >= 50:
                    increasing = False
            else:
                intensity -= 5
                if intensity <= 0:
                    increasing = True
            
            glow_color = constants.GLOW_COLOR if intensity > 25 else original_border_color
            try:
                widget.configure(border_color=glow_color)
            except:
                pass
            
            root.after(50, lambda: pulse_glow(increasing, intensity))
        
        return pulse_glow
    
    def add_focus_glow(widget):
        glow_function = create_glow_effect(widget)
        
        def on_focus_in(e):
            glow_function()
        
        def on_focus_out(e):
            try:
                widget.configure(border_color=constants.BORDER_COLOR)
            except:
                pass
        
        widget.bind("<FocusIn>", on_focus_in)
        widget.bind("<FocusOut>", on_focus_out)
    
    
    add_focus_glow(target_hash_entry)

    return root

def main():
    import threading
    stop_event_ref = threading.Event()
    
    root = create_gui(stop_event_ref)
    root.mainloop()

if __name__ == "__main__":
    main()