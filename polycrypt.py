import hashlib
import string
import tkinter as tk
import re
from tkinter import ttk, messagebox
from concurrent.futures import ThreadPoolExecutor
import subprocess
from passlib.hash import bcrypt as passlib_bcrypt
from ttkthemes import ThemedTk
import tkinter.filedialog as tkfiledialog

def crack_password(target_hash, wordlist_path, max_password_length):
    charset = string.ascii_letters + string.digits + string.punctuation

    def hash_password(password, hash_function):
        return hash_function(password.encode()).hexdigest()

    # Dictionary of supported hash algorithms and their corresponding hashlib functions
    hash_algorithms = {
        'MD5': hashlib.md5,
        'SHA-1': hashlib.sha1,
        'SHA-224': hashlib.sha224,
        'SHA-256': hashlib.sha256,
        'SHA-384': hashlib.sha384,
        'SHA-512': hashlib.sha512,
        'SHA3-256': hashlib.sha3_256,
        'SHA3-384': hashlib.sha3_384,
        'SHA3-512': hashlib.sha3_512,
    }

    # Function to detect the hash type
    def detect_hash_type(target_hash):
        try:
            output = subprocess.check_output(['hashid', target_hash])
            lines = output.decode('utf-8').strip().split('\n')
            if len(lines) > 1 and lines[1].startswith('[+]'):
                detected_hash = lines[1].split('[+]')[1].strip()
                if detected_hash in hash_algorithms:
                    return detected_hash
            if target_hash.startswith("$2a$") or target_hash.startswith("$2b$") or target_hash.startswith("$2y$"):
                return "bcrypt"
            # If the detected hash is not in hash_algorithms, check its length and find a match
            for algorithm, hash_function in hash_algorithms.items():
                if len(target_hash) == len(hash_password('', hash_function)):
                    return algorithm
        except Exception:
            pass
        return None

    def crack_with_bcrypt(wordlist_path, target_hash, max_password_length):
     with open(wordlist_path, 'r') as wordlist_file:
        for word in wordlist_file:
            password = word.strip()
            # Extract the number of rounds from the target hash using a regular expression
            match = re.search(r'^\$2[aby]?\$(\d+)\$', target_hash)
            if match:
                rounds = int(match.group(1))  # Extract the number of rounds
                if len(password) <= max_password_length and passlib_bcrypt.verify(password, target_hash):
                    return f"\nAlgorithm: Bcrypt (Rounds: {rounds}), Password: {password}"

    hash_type = detect_hash_type(target_hash)
    if hash_type is None:
        return None
            
    if hash_type == "bcrypt":
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda algo_func: crack_with_bcrypt(*algo_func), [(wordlist_path, target_hash, max_password_length)]))

        return next((result for result in results if result), None)
        
    # Crack password using the wordlist and transformations for the specific hash type
    def crack_with_algorithm(algorithm, hash_function, max_password_length):
        with open(wordlist_path, 'r') as wordlist_file:
            for password in wordlist_file:
                password = password.strip()

                if len(password) > max_password_length:
                    continue  # Skip passwords exceeding max length

                hashed_password = hash_password(password, hash_function)

                if hashed_password == target_hash:
                    return f"\nAlgorithm: {algorithm}, Password: {password}"

                transformed_passwords = [password, password.upper(), password.lower(), password.capitalize(), password[::-1]]
                for transformed_password in transformed_passwords:
                    hashed_transformed_password = hash_password(transformed_password, hash_function)

                    if hashed_transformed_password == target_hash:
                        return f"\nAlgorithm: {algorithm}, Password: {transformed_password}"

    # Perform password cracking for the detected hash type
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda algo_func: crack_with_algorithm(*algo_func), [(hash_type, hash_algorithms[hash_type], max_password_length)]))

    return next((result for result in results if result), None)

def on_crack_button_click():
    target_hash = target_hash_entry.get()
    wordlist_path = wordlist_path_entry.get()
    max_password_length = int(max_password_length_entry.get())

    result_label.config(text="Searching, please wait...")
    root.update()  # Update the GUI to show the starting message

    result = crack_password(target_hash, wordlist_path, max_password_length)

    if result:
        result_label.config(text=result)
    else:
        result_label.config(text="Password not found in the wordlist.")
        
def browse_wordlist_path():
    file_path = tk.filedialog.askopenfilename(filetypes=[])
    if file_path:
        wordlist_path_entry.delete(0, tk.END)
        wordlist_path_entry.insert(0, file_path)
        
# Create the themed GUI
root = ThemedTk(theme="equilux")
root.title("Polycrypt: @yanpuri")
root.iconbitmap("C:/Users/pc/Downloads/lock_open_FILL0_wght400_GRAD0_opsz48.ico")  # Path to your icon
root.geometry("550x270")

frame = ttk.Frame(root, padding="20")
frame.pack(fill=tk.BOTH, expand=True)

# Styling options for labels and entries
label_style = ttk.Style()
label_style.configure("Label.TLabel", foreground="white")
entry_style = ttk.Style()
entry_style.configure("Entry.TEntry", fieldbackground="white")

# Apply styles to labels and entries
target_hash_label = ttk.Label(frame, text="Target Hash:", style="Label.TLabel")
target_hash_label.pack()

target_hash_entry = ttk.Entry(frame, width=50, style="Entry.TEntry")
target_hash_entry.pack()

wordlist_path_frame = ttk.Frame(frame)
wordlist_path_frame.pack(fill="x")

wordlist_path_label = ttk.Label(wordlist_path_frame, text="Wordlist Path:", style="Label.TLabel")
wordlist_path_label.pack()

wordlist_path_entry = ttk.Entry(wordlist_path_frame, width=50, style="Entry.TEntry")
wordlist_path_entry.pack()

browse_button = ttk.Button(wordlist_path_frame, text="Browse", command=browse_wordlist_path)
browse_button.pack(side="right")
browse_button.place(x=420, y=11)

browse_button_style = ttk.Style()
browse_button_style.configure("Browse.TButton", foreground="white", background="#b8b8b8")
browse_button_style.map("Browse.TButton", background=[("active", "#45a049")])
browse_button["style"] = "Browse.TButton"

max_password_length_label = ttk.Label(frame, text="Max Password Length:", style="Label.TLabel")
max_password_length_label.pack()

max_password_length_entry = ttk.Entry(frame, width=50, style="Entry.TEntry")
max_password_length_entry.pack()

# Customized button style
ttk.Separator(frame, orient='horizontal').pack(pady=5)
crack_button = ttk.Button(frame, text="Crack Password", command=on_crack_button_click)
crack_button.pack()
crack_button_style = ttk.Style()
crack_button_style.configure("CrackButton.TButton", foreground="white", background="#b8b8b8")
crack_button_style.map("CrackButton.TButton", background=[("active", "#45a049")])
crack_button["style"] = "CrackButton.TButton"

# Styling options for the result label
result_label = ttk.Label(frame, text="", wraplength=450, justify=tk.LEFT, style="Label.TLabel")
result_label.pack()

root.mainloop()