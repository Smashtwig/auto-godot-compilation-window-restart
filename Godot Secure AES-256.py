import os
import sys
import random
import string

def patch_godot():
    # Use the path provided by the YML or default to ./godot
    godot_path = sys.argv[1] if len(sys.argv) > 1 else "./godot"
    
    target_file = os.path.join(godot_path, "core/io/file_access_encrypted.cpp")
    header_file = os.path.join(godot_path, "core/crypto/security_token.h")

    print(f"--- STARTING SECURE PATCH ---")
    print(f"Targeting: {target_file}")

    if not os.path.exists(target_file):
        print(f"!! ERROR: CANNOT FIND GODOT SOURCE AT {target_file} !!")
        sys.exit(1)

    # 1. GENERATE TOKEN
    token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    token_hex = ', '.join([f"0x{ord(c):02x}" for c in token])
    
    # 2. CREATE HEADER
    header_content = f'#ifndef SECURITY_TOKEN_H\n#define SECURITY_TOKEN_H\n#include "core/typedefs.h"\nstatic const uint8_t SECURITY_TOKEN[32] = {{ {token_hex} }};\n#endif'
    with open(header_file, "w") as f:
        f.write(header_content)
    print(f"CHECK: Security Token Header created.")

    # 3. PATCH CPP
    with open(target_file, "r") as f:
        content = f.read()

    # Define the changes
    include_patch = '#include "core/io/file_access_encrypted.h"\n#include "core/crypto/security_token.h"'
    # We look for the specific loop where Godot handles the 32-byte key
    logic_find = 'for (int i = 0; i < 32; i++) {'
    logic_patch = 'for (int i = 0; i < 32; i++) {\n\t\t\tkey[i] ^= SECURITY_TOKEN[i];'

    if include_patch in content or logic_patch in content:
        print("CHECK: File already patched.")
    else:
        content = content.replace('#include "core/io/file_access_encrypted.h"', include_patch)
        content = content.replace(logic_find, logic_patch)

    # VERIFY
    if 'SECURITY_TOKEN' in content:
        with open(target_file, "w") as f:
            f.write(content)
        print("CHECK: file_access_encrypted.cpp successfully patched.")
        print(f"TOKEN_SAMPLED_FOR_VERIFICATION: {token[:5]}...")
    else:
        print("!! FATAL ERROR: COULD NOT INJECT SECURITY LOGIC !!")
        sys.exit(1)

if __name__ == "__main__":
    patch_godot()
