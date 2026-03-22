with open("app2_v2.py", "r") as f:
    content = f.read()

old_instruction = "Desenvolva entre 5 e 15 capítulos principais."
new_instruction = "PARA FINS DE TESTE RAPIDO (EVITAR TIMEOUT DA REDE DO USUARIO), GERE APENAS UM ÚNICO CAPÍTULO MUITO CURTO (2 parágrafos no máximo) e encerre a geração."

if old_instruction in content:
    content = content.replace(old_instruction, new_instruction)
    with open("app2_v2.py", "w") as f:
        f.write(content)
    print("Prompt patched for speed/timeout avoidance.")
else:
    print("Instruction not found!")
