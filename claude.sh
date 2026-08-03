#!/bin/bash

# Claude Code bu modeli kullanarak kod analizi ve üretimi yapacak.
MY_MODEL="gemma4:e2b"

# Kod üretiminde stabiliteyi artırır. Düşük değer, daha tahmin edilebilir kod üretir.
export OLLAMA_TEMPERATURE=0.2

# Claude Code'un bağlanacağı yerel Ollama sunucusunun API adresi.
export ANTHROPIC_BASE_URL="http://localhost:11434/v1"

# Claude Code'un Ollama ile iletişim kurabilmesi için gerekli anahtar.
export ANTHROPIC_API_KEY="ollama"

# Kullanılacak modelin adı, Claude Code ve alt ajanlar için geçerlidir.
export ANTHROPIC_MODEL="$MY_MODEL"

# Alt ajan olarak Claude Code içinde kullanılacak modelin adı.
export CLAUDE_CODE_SUBAGENT_MODEL="$MY_MODEL"

# Proje bazlı özel ayarları atlar; tüm projeler için aynı genel ayar geçerli olur.
export CLAUDE_CODE_SKIP_PROJECT_SETTINGS=1

# Claude Code’un sistem promptunu aktif eder, modelin davranışı önceden belirlenmiş yönergelere göre olur.
export CLAUDE_CODE_USE_SYSTEM_PROMPT=1

# Modelin nasıl davranacağını tanımlar; kod yazarken rehber olarak kullanılır.
export ANTHROPIC_CUSTOM_PROMPT="
You are a local AI software engineer running inside Claude Code.
Rules:
- Inspect repository before coding.
- Use file reading tools.
- Prefer editing existing files.
- Avoid hallucinating APIs.
- Explain which files you will modify before writing code.
- Focus on clean, maintainable and production-ready code.
- Do not use google_search.
"

# Claude Code'u başlatır ve kullanılan modeli ekrana yazdırır.
echo "Claude Code local model ile başlatılıyor..."
echo "Model: $MY_MODEL"
ollama launch claude --model "$MY_MODEL"