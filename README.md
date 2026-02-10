# Sistema de Gestão de Pedidos

Sistema em Python com interface gráfica (Tkinter) para gerenciar pedidos de produtos por setor.

## 📋 Funcionalidades

- ✅ Carregar planilha Excel com produtos e setores
- ✅ Selecionar setor/cliente
- ✅ Buscar e adicionar produtos ao pedido
- ✅ Definir quantidades
- ✅ Visualizar carrinho com valores
- ✅ Gerar pedido automaticamente
- ✅ Salvar pedidos na planilha Excel

## 🚀 Como Usar

### 1. Instalação das Dependências

```bash
pip install pandas openpyxl --break-system-packages
```

### 2. Executar o Programa

```bash
python3 sistema_pedidos.py
```

### 3. Fluxo de Trabalho

1. **Carregar Planilha**: Clique em "📁 Selecionar Arquivo Excel" e escolha sua planilha
2. **Selecionar Setor**: Escolha o setor/cliente no dropdown
3. **Adicionar Produtos**: 
   - Use a busca para filtrar produtos
   - Clique duplo no produto OU selecione e clique "➕ Adicionar ao Pedido"
   - Defina a quantidade desejada
4. **Revisar Pedido**: Veja os itens no carrinho com valores calculados
5. **Finalizar**: Clique em "✅ Gerar Pedido e Salvar"

## 📊 Estrutura da Planilha

### Aba: Produtos
- `productCode`: Código do produto
- `name`: Nome do produto
- `price`: Preço unitário
- `product_id`: ID único do produto

### Aba: Setor
- `CódUnidade`: Código do setor
- `items__description`: Descrição do setor

### Aba: ItensPedido (gerada automaticamente)
- `pedido_id`: ID do pedido
- `codigo`: Código do produto
- `produto`: Nome do produto
- `qtd`: Quantidade
- `valor_unit`: Valor unitário
- `total_item`: Total do item (qtd × valor_unit)

### Aba: Pedido (gerada automaticamente)
- `pedido_id`: ID único do pedido
- `data`: Data e hora do pedido
- `cliente`: Setor selecionado
- `supervisora`: Campo para supervisor (vazio por padrão)
- `status`: Status do pedido (padrão: "Aguardando aprovação")
- `total_pedido`: Valor total do pedido

## 🎯 Detalhes Importantes

- **Código Cliente Impakto**: Fixado em `208831` conforme especificação
- **Cálculo Automático**: O sistema calcula automaticamente:
  - Total por item (Quantidade × Preço Unitário)
  - Total do pedido (soma de todos os itens)
- **ID Único**: Cada pedido recebe um ID único de 8 caracteres
- **Backup**: A planilha é atualizada diretamente, mantenha backups!

## ⚙️ Funcionalidades Adicionais

- 🔍 **Busca de Produtos**: Filtre produtos por nome ou código
- 🗑️ **Remover Items**: Remova items individuais ou limpe todo o carrinho
- 💰 **Total em Tempo Real**: Veja o valor total sendo atualizado
- ✏️ **Edição de Quantidade**: Use o spin box para definir quantidades

## 🐛 Solução de Problemas

### Erro ao carregar planilha
- Verifique se o arquivo tem as abas: "Produtos" e "Setor"
- As abas "Pedido" e "ItensPedido" serão criadas automaticamente se não existirem

### Erro ao salvar
- Feche a planilha Excel antes de gerar o pedido
- Verifique permissões de escrita no arquivo

## 📝 Exemplo de Uso

1. Abra o programa
2. Carregue a planilha `Cópia_de_Sync_Produtos.xlsx`
3. Selecione "38 - ABRINQ" como setor
4. Busque "caneta" na caixa de busca
5. Dê duplo clique no produto desejado
6. Ajuste a quantidade para 10
7. Adicione mais produtos se necessário
8. Clique em "Gerar Pedido e Salvar"
9. Pedido salvo com sucesso!

## 🌐 Versão Web (Streamlit)

Para disponibilizar o sistema via navegador (ex.: Railway, Render ou execução local), utilize o app em [streamlit_app.py](streamlit_app.py).

### Executar localmente

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Variáveis de ambiente importantes

- `ORDERS_WORKBOOK_PATH`: caminho absoluto da planilha que o app deve carregar automaticamente quando estiver hospedado.
- Outras credenciais ou chaves podem ser definidas como variáveis de ambiente do serviço (Railway/Render) e lidas pelo app conforme necessário.

### Deploy rápido no Railway ou Render

1. Faça fork/clonagem do repositório e confirme que o app roda com `streamlit run streamlit_app.py`.
2. No painel do Railway/Render, escolha "Deploy from GitHub" e selecione este projeto.
3. Configure o comando de start como `streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0`.
4. Cadastre as variáveis de ambiente (por exemplo, `ORDERS_WORKBOOK_PATH`, chaves de API, etc.) na área de "Secrets" do serviço.
5. Após o deploy, compartilhe a URL gerada apenas com usuários autorizados (adicione autenticação básica/Cloudflare Access se precisar restringir o acesso).

## 📞 Suporte

Em caso de dúvidas ou problemas, verifique:
- Versão do Python (3.x requerido)
- Pacotes instalados corretamente
- Formato da planilha Excel

---

**Desenvolvido com Python 3 + Tkinter + Pandas**
