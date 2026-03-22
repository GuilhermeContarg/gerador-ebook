with open("ebook_v2.js", "r") as f:
    content = f.read()

old_json_logic = """
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Erro no servidor ao gerar eBook.");
            }
"""

new_json_logic = """
            let data = {};
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                data = await response.json();
            } else {
                const textError = await response.text();
                console.error("Servidor retornou não-JSON:", textError);
                throw new Error("Erro Crítico no Servidor: Timeout ou Chave de API Inválida (Consulte os logs). O Servidor não retornou JSON.");
            }

            if (!response.ok) {
                throw new Error(data.error || "Erro no servidor ao gerar eBook.");
            }
"""

if old_json_logic in content:
    content = content.replace(old_json_logic, new_json_logic)
    with open("ebook_v2.js", "w") as f:
        f.write(content)
    print("Patched JS.")
else:
    print("Could not find exact block. Check JS.")
