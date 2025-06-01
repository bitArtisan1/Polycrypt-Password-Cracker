<p align="center">
  <a href="https://ko-fi.com/D1D11CZNM1">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" />
  </a>
</p>

# PolycryptZero (p0) - Hash Decryption Tool

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.0-orange.svg)](https://github.com/bitArtisan1/p0-Decryption-Tool/releases)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

A hash cracking tool with GUI that supports multiple attack methods and hash algorithms. It includes support for a probabilistic mode which uses a GPT2 style autoregressive transformer model, trained for password generation and prediction.

<p align="center">
  <img src="https://github.com/user-attachments/assets/2c6cce0f-dd50-4462-84b4-778718667444" alt="Alt text" width="300"/>
</p>

## ✨ Features

- 🔐 **Attack Modes**: Wordlist, Brute-force, Rule-based, AI-powered probabilistic, Rainbow tables
- 🔒 **Hash Support**: MD5, SHA family, bcrypt, BLAKE2, and 20+ other algorithms  
- 🤖 **AI Integration**: Custom GPT2 ML model for intelligent password generation and completion
- 🌈 **Rainbow Tables**: Bloom filter optimized storage with SQLite backend
- 🎨 **Modern GUI**: Dark theme interface with real-time progress tracking

`Probablistic` mode uses an autoregressive transformer model, similar to GPT-2, for sequential data analysis:

**Key Features: (check src/train.py)**

*   **Transformer Architecture:** Employs multi-layer, multi-head self-attention mechanisms.
*   **Generative:** Predicts subsequent elements in a sequence.
*   **Configurable:** Core parameters like layers, attention heads, and embedding dimensions can be adjusted.
  
## 📦 Installation

### Option 1: Executable (Windows)
Download the latest release from [Releases](https://github.com/bitArtisan1/p0-Decryption-Tool/releases/tag/v1.0.0) and run `PolycryptZero.exe` - no Python required.

### Option 2: Python Source
```bash
git clone https://github.com/bitArtisan1/p0-Decryption-Tool.git
cd p0-Decryption-Tool
pip install -r requirements.txt
python src/main.py
```

#### 📋 Requirements

- **Python**: 3.11+
- **Dependencies**: `customtkinter`, `pycryptodome`, `numpy`, `onnxruntime`, `transformers`


## 🚀 Usage

1. Enter target hash
2. Select hash algorithm 
3. Choose attack mode
4. Configure parameters (wordlist, character set, etc.)
5. Start attack

For `Wordlist` and `Rule-Based` modes, you need a passwords wordlist to test against (e.g: `rockyou.txt`):

```cmd
curl -LO https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
```

For probablistic mode, choose the provided `onnx_model-output` directory

## ⚔️ Attack Modes

- 📚 **Wordlist**: Dictionary attack using password lists 
- 💪 **Brute-force**: Try all possible combinations
- ⚙️ **Rule-based**: Apply transformations to wordlist (capitalization, leet speak, etc.)
- 🧠 **Probabilistic**: AI model generates likely passwords, use provided `onnx_model_output` path
- 🌈 **Rainbow Table**: Precomputed hash lookups

## TODO

- Improve model architecture for better pattern matching
- Add linux support release
- Add CUDA GPU support for probablistic attack mode

## GUI

![p0](https://github.com/user-attachments/assets/96a9679e-bae8-4ffb-9f8c-9fc48e43cf8a)

## Legal Notice

This password cracker tool, PolycryptZero™, is intended for educational and personal use only. The tool is designed to demonstrate the concepts of password hashing, security vulnerabilities, and password cracking techniques. 

By using this tool, you acknowledge that:

- You are solely responsible for how you use this tool and any consequences that may arise from its use.
- Unauthorized use of this tool to access or attempt to access accounts, systems, or data that you do not have explicit permission to access is prohibited.
- The developers of this tool are not responsible for any legal or ethical issues that may result from the misuse of this tool.
- This tool should not be used for any malicious, illegal, or unethical activities.

Please use this tool responsibly and in compliance with applicable laws and regulations. The developers of this tool disclaim any liability for improper or illegal use.
The name PolycryptZero™ and logo are not part of the open-source license and may not be used in derivative projects or forks without permission.

## Support Me
If you find this useful

- Starring the repository on GitHub
- Sharing the tool with others
- Providing feedback and suggestions
- Follow me for more :)

<a href="https://ko-fi.com/D1D11CZNM1">
  <img src="https://github.com/user-attachments/assets/ba118768-9054-416f-b7b2-adaa69a53434" alt="Support me on Ko-fi" width="200" />
</a>
    
---
For any issues or feature requests, please open an issue on GitHub. Happy coding!
<center>
<div style="text-align: center;">
  <p align="center">
    <img src="https://github.com/user-attachments/assets/74c55d3e-6985-4a8a-afbd-46cc33e54e73" alt="octodance" width="110" height="110" style="margin-right: 100px;"/>
    <img src="https://github.com/user-attachments/assets/aeeda621-8287-4f89-bed3-8b89e09f85a5" alt="octodance" width="100" height="100"/>
  </p>
</div>
</center>

