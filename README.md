# Polycrypt Password Cracking Tool
A straightforward yet effective password cracker tool with multi-threading developed in Python, utilizing the user-friendly Tkinter GUI framework to provide an intuitive and interactive graphical interface.

## Features

- Supports multiple hash algorithms, including MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512, SHA3-256, SHA3-384, SHA3-512, and Bcrypt.
- Case-insensitive search
- Uses efficient data structures for transformed passwords for faster membership checking.
- Performs password cracking using wordlists and various password transformations (upper, lower, capitalize, reverse).
- Interactive GUI for easier, clearer, faster, cracking
- Multithreading and ThreadPoolingExecuoter
- Hash-type detection system

## Usage

1. Clone the repository:
```
git clone https://github.com/yanpuri/Polycrypt-Password-Cracker.git
cd Polycrypt-Password-Cracker
```
2. Install the required libraries
```python
pip install passlib ttkthemes
```
3. Run the password cracker:
```python
python polycrypt.py
```

## Notes

* I have included the 10-million most common passwords & the 1000-most common passwords lists in this repository for quick reference and accuracy
* I plan to add support for a dozen more hashes in the future
* Improve the data structures used
* Use more optimization techniques and algorithms for faster results

## Images:

### SHA-512 Algorithm Cracking:
![sha512](https://github.com/yanpuri/Polycrypt-Password-Cracker/assets/121260820/7feb603c-bf83-4631-b560-9993cc3097dc)
### Bcrypt Algorithm Cracking:
![bcrypt](https://github.com/yanpuri/Polycrypt-Password-Cracker/assets/121260820/bb6c4bd8-7f8f-43b3-b3e3-dd2270a95c4a)

## Legal Notice

This password cracker tool, Polycrypt, is intended for educational and personal use only. The tool is designed to demonstrate the concepts of password hashing, security vulnerabilities, and password cracking techniques. 

By using this tool, you acknowledge that:

- You are solely responsible for how you use this tool and any consequences that may arise from its use.
- Unauthorized use of this tool to access or attempt to access accounts, systems, or data that you do not have explicit permission to access is prohibited.
- The developers of this tool are not responsible for any legal or ethical issues that may result from the misuse of this tool.
- This tool should not be used for any malicious, illegal, or unethical activities.

Please use this tool responsibly and in compliance with applicable laws and regulations. The developers of this tool disclaim any liability for improper or illegal use.

## License

This password cracker tool is open-source software released under the [GNU General Public License version 3 (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.en.html). You are free to use, modify, and distribute this software in accordance with the terms of the GPLv3 license.

Please review the [GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.en.html) to understand your rights and responsibilities when using this software.
