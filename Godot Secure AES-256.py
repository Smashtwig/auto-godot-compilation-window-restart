import os
import sys
import random
import string
import binascii
import secrets
import datetime

class LogColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
def generate_random_tag(length=4):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def generate_random_token(length=32):
    return bytes([random.randint(0, 255) for _ in range(length)])

def hex_to_bytes(hex_string: str) -> bytes:
    return bytes.fromhex(hex_string)

def generate_magic_header(tag: str, endian='little') -> str:
    if len(tag) != 4:
        raise ValueError("Tag must be exactly 4 characters.")
    if endian == 'little':
        tag = tag[::-1]
    hex_value = "0x" + ''.join(f"{ord(c):02X}" for c in tag)
    return hex_value

def build_random_key_derivation():
    operands = ["key_ptr[i]", "Security::TOKEN[i]"]
    base_ops = [
        "({a} ^ {b})", "({a} + {b})", "({a} | {b})", "({a} & {b})",
        "(({a} << {shift}) | ({a} >> {rshift}))", "(({a} ^ {b}) + {const})", "(({a} + {b}) ^ {const})",
    ]
    chain_ops = [
        "({expr} ^ {value})", "({expr} + {value})", "({expr} | {value})",
        "(({expr} << {shift}) | ({expr} >> {rshift}))", "(({expr} ^ {value}) + {const})", "(({expr} + {value}) ^ {const})",
    ]
    def rotation():
        shift = secrets.randbelow(7) + 1
        return shift, 8 - shift
    def rand_const():
        return secrets.randbelow(255) + 1
    layers = secrets.randbelow(5) + 2
    a = secrets.choice(operands)
    b = operands[1] if a == operands[0] else operands[0]
    shift, rshift = rotation()
    expression = secrets.choice(base_ops).format(a=a,b=b,shift=shift,rshift=rshift,const=rand_const())
    for _ in range(layers - 1):
        shift, rshift = rotation()
        value = secrets.choice(operands)
        if value == expression:
            value = secrets.choice(operands)
        expression = secrets.choice(chain_ops).format(expr=expression,value=value,shift=shift,rshift=rshift,const=rand_const())
    return f"token_key.write[i] = (uint8_t)({expression});"

def save_log(message):
    if not str(message).find("\033[") > 0:
        with open(logFileName,"a", encoding="utf-8") as logf: logf.write(f"{message}\n")
    return message

def print_success(message):
    save_log(f"      [✓] {message}")
    print(f"{LogColors.OKGREEN}      ✓{LogColors.ENDC} {message}")

def print_error(message):
    save_log(f"      [✗] {message}\n")
    print(f"{LogColors.FAIL}      ✗{LogColors.ENDC} {message}")

def print_info(message):
    save_log(f"\n[INFO] -   {message}")
    print(f"\n{LogColors.OKBLUE} ℹ {LogColors.ENDC} {message}")
    
def print_operation(message):
    save_log(f"   [=>] {message}")
    print(f"{LogColors.HEADER}   =>{LogColors.ENDC} {message}")

def print_warning(message):
    save_log(f"\n[WARN] -   {message}")
    print(f"\n{LogColors.WARNING} ⚠ {LogColors.ENDC} {message}")

# --- SETUP ---
baseTag = generate_random_tag()
encTag = generate_random_tag()
security_token = generate_random_token()
token_hex = binascii.hexlify(security_token).decode('utf-8')
token_c_array = ', '.join([f'0x{b:02X}' for b in security_token])
baseHeader = generate_magic_header(baseTag)
encHeader = generate_magic_header(encTag)
key_derivation_algorithm = build_random_key_derivation() # Default to Advanced

fileCreated = True
backup_path = None
current_dt = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
logFileName = f"Log-{current_dt}-Godot-Secure-AES.txt"

if len(sys.argv) == 1:
    godot_root = os.getcwd()
elif len(sys.argv) == 2:
    godot_root = sys.argv[1]
else:
    sys.exit(1)

with open(logFileName, "w", encoding="utf-8") as logf: 
    logf.write(f"Created On - {current_dt}\nAutomation Mode: ON\n\n")

try:
    encKey = os.environ["SCRIPT_AES256_ENCRYPTION_KEY"]
except:
    encKey = "MISSING_ENV_VAR"

# Modification logic is now strictly forced for automation
MODIFICATIONS = [
    {"file": "version.py", "operations": [{"type": "replace_line", "description": "Mod title", "find": "name = \"Godot Engine\"", "replace": "name = \"Godot Engine (With Godot Secure)\""}]},
    {"file": "editor/export/project_export.cpp", "operations": [{"type": "replace_line", "description": "Mod export title", "find": "set_title(TTR(\"Export\"));", "replace": "set_title(TTR(\"Export With Godot Secure (AES-256)\"));"}]},
    {"file": "core/crypto/security_token.h", "operations": [{"type": "create_file", "description": "Create security token header", "content": ["#ifndef SECURITY_TOKEN_H", "#define SECURITY_TOKEN_H", "", "#include \"core/typedefs.h\"", "", "namespace Security {", f"    static const uint8_t TOKEN[32] = {{ {token_c_array} }};", "};", "", "#endif"]}]},
    {"file": "core/io/file_access_pack.h", "operations": [{"type": "replace_line", "description": "Mod Pack Magic", "find": "#define PACK_HEADER_MAGIC 0x43504447", "replace": f"#define PACK_HEADER_MAGIC {baseHeader}"}]},
    {"file": "core/io/file_access_encrypted.h", "operations": [{"type": "replace_line", "description": "Mod Enc Magic", "find": "#define ENCRYPTED_HEADER_MAGIC 0x43454447", "replace": f"#define ENCRYPTED_HEADER_MAGIC {encHeader}"}]},
    {
        "file": "core/io/file_access_encrypted.cpp", 
        "operations": [
            {"type": "insert_after", "description": "Include header", "find": "#include \"file_access_encrypted.h\"", "replace": "#include \"core/crypto/security_token.h\""},
            {"type": "replace_block", "description": "Mod Decryption", "find": ["{", "CryptoCore::AESContext ctx;", "", "ctx.set_encode_key(key.ptrw(), 256); // Due to the nature of CFB, same key schedule is used for both encryption and decryption!", "ctx.decrypt_cfb(ds, iv.ptrw(), data.ptrw(), data.ptrw());", "}"], "replace": ["{", "CryptoCore::AESContext ctx;", "    Vector<uint8_t> token_key;", "    token_key.resize(32);", "    const uint8_t *key_ptr = key.ptr();", "    for (int i = 0; i < 32; i++) {", f"        {key_derivation_algorithm}", "    }", "    ctx.set_encode_key(token_key.ptrw(), 256);", "    ctx.decrypt_cfb(ds, iv.ptrw(), data.ptrw(), data.ptrw());", "}"]},
            {"type": "replace_block", "description": "Mod Encryption", "find": ["CryptoCore::AESContext ctx;", "ctx.set_encode_key(key.ptrw(), 256);", "", "if (use_magic) {", "    file->store_32(ENCRYPTED_HEADER_MAGIC);", "}", "", "file->store_buffer(hash, 16);", "file->store_64(data.size());", "file->store_buffer(iv.ptr(), 16);", "", "ctx.encrypt_cfb(len, iv.ptrw(), compressed.ptr(), compressed.ptr());"], "replace": ["CryptoCore::AESContext ctx;", "    Vector<uint8_t> token_key;", "    token_key.resize(32);", "    const uint8_t *key_ptr = key.ptr();", "    for (int i = 0; i < 32; i++) {", f"        {key_derivation_algorithm}", "    }", "    ctx.set_encode_key(token_key.ptrw(), 256);", "if (use_magic) {", "file->store_32(ENCRYPTED_HEADER_MAGIC);", "}", "file->store_buffer(hash, 16);", "file->store_64(data.size());", "file->store_buffer(iv.ptr(), 16);", "ctx.encrypt_cfb(len, iv.ptrw(), compressed.ptr(), compressed.ptr());"]}
        ]
    }
]

def apply_modifications(root_dir):
    step = 0
    for mod in MODIFICATIONS:
        file_path = os.path.join(root_dir, mod["file"])
        step += 1
        if any(op.get("type") == "create_file" for op in mod["operations"]):
            for op in mod["operations"]:
                if op["type"] == "create_file":
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w") as f:
                        f.write("\n".join(op["content"]) if isinstance(op["content"], list) else op["content"])
                    print_success(f"Forced creation: {file_path}")
            continue

        if not os.path.exists(file_path):
            print_error(f"Missing: {file_path}")
            continue

        with open(file_path, "r") as f: lines = f.readlines()
        modified = False
        for op in mod["operations"]:
            if op["type"] == "replace_line":
                find = op["find"].strip()
                for i in range(len(lines)):
                    if lines[i].strip() == find:
                        lines[i] = op["replace"] + "\n"
                        modified = True
                        break
            elif op["type"] == "replace_block":
                find_lines = [ln.strip() for ln in op["find"]]
                for i in range(len(lines) - len(find_lines) + 1):
                    if all(lines[i + j].strip() == find_lines[j] for j in range(len(find_lines))):
                        lines[i:i + len(find_lines)] = [ln + "\n" for ln in op["replace"]]
                        modified = True
                        break
            elif op["type"] == "insert_after":
                find = op["find"].strip()
                for i in range(len(lines)):
                    if lines[i].strip() == find:
                        lines.insert(i+1, op["replace"] + "\n")
                        modified = True
                        break
        if modified:
            with open(file_path, "w") as f: f.writelines(lines)
            print_success(f"Patched: {file_path}")

if __name__ == "__main__":
    apply_modifications(godot_root)
    print("Automation Complete.")
    sys.exit(0)
