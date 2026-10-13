#!/bin/bash
# Script de inicialização para teste do scraper corrigido
# Este script limpa o ambiente e executa o teste com 3 páginas

echo "╔════════════════════════════════════════════════════════╗"
echo "║  🔧 TESTE DO SCRAPER CORRIGIDO (3 páginas)           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# Limpar logs e cache antigos
echo "🧹 Limpando cache antigo..."
rm -rf .scrapy .cache __pycache__ 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ Cache limpo"
echo ""

# Limpar dados antigos (opcional)
# rm -f data.json data_instock.json data_outofstock.json

echo "🚀 Iniciando scraper..."
echo "⚙️  Configuração: CLOSESPIDER_PAGECOUNT = 3"
echo "📊 Limite de páginas: 3 (para validação)"
echo ""

# Executar scrapy
python -m scrapy crawl wedrop --loglevel=INFO

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ Execução concluída!                               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Arquivos gerados:"
echo "   • data.json (itens extraídos)"
echo ""

# Mostrar estatísticas
if [ -f data.json ]; then
    echo "📊 Itens extraídos:"
    grep -c '"product_id"' data.json || echo "   Nenhum item extraído ainda"
else
    echo "⚠️  Arquivo data.json não encontrado"
fi

echo ""
echo "💡 Próximos passos:"
echo "   1. Verifique se há itens em data.json"
echo "   2. Se OK, remova a linha CLOSESPIDER_PAGECOUNT em Site/settings.py"
echo "   3. Execute: python -m scrapy crawl wedrop"
echo ""
