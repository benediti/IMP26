#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIA RÁPIDO - Sistema de Gestão de Pedidos

Este arquivo demonstra o fluxo de uso do sistema.
"""

# ====================================================================
# PASSO 1: CARREGAR A PLANILHA
# ====================================================================
print("=" * 70)
print("PASSO 1: CARREGAR A PLANILHA")
print("=" * 70)
print("""
1. Clique no botão '📁 Selecionar Arquivo Excel'
2. Navegue até sua planilha Excel
3. Selecione o arquivo 'Cópia_de_Sync_Produtos.xlsx'
4. Aguarde a mensagem de sucesso
""")

# ====================================================================
# PASSO 2: SELECIONAR SETOR/CLIENTE
# ====================================================================
print("\n" + "=" * 70)
print("PASSO 2: SELECIONAR SETOR/CLIENTE")
print("=" * 70)
print("""
1. No dropdown 'Setor', você verá todos os setores disponíveis
2. Selecione o setor desejado, por exemplo: '38 - ABRINQ'
3. Este será o cliente do pedido
""")

# ====================================================================
# PASSO 3: ADICIONAR PRODUTOS
# ====================================================================
print("\n" + "=" * 70)
print("PASSO 3: ADICIONAR PRODUTOS")
print("=" * 70)
print("""
Existem 3 formas de adicionar produtos:

FORMA 1: Duplo Clique
   - Dê duplo clique no produto desejado na lista
   
FORMA 2: Seleção + Botão
   - Clique uma vez no produto
   - Ajuste a quantidade no campo 'Quantidade'
   - Clique em '➕ Adicionar ao Pedido'
   
FORMA 3: Com Busca
   - Digite na caixa 'Buscar' para filtrar produtos
   - Exemplo: digite 'caneta' para ver só canetas
   - Selecione e adicione como nas formas anteriores
""")

# ====================================================================
# PASSO 4: REVISAR CARRINHO
# ====================================================================
print("\n" + "=" * 70)
print("PASSO 4: REVISAR CARRINHO")
print("=" * 70)
print("""
No lado direito você verá:
- Código do produto
- Nome do item
- Quantidade
- Preço unitário
- Total do item (Qtd × Preço)

O total geral aparece na parte inferior.

Você pode:
- Remover um item específico: selecione e clique '🗑️ Remover Item'
- Limpar tudo: clique '🗑️ Limpar Tudo'
""")

# ====================================================================
# PASSO 5: GERAR PEDIDO
# ====================================================================
print("\n" + "=" * 70)
print("PASSO 5: GERAR PEDIDO")
print("=" * 70)
print("""
1. Revise o total do pedido
2. Clique em '✅ Gerar Pedido e Salvar'
3. O sistema irá:
   - Criar um ID único para o pedido
   - Salvar na aba 'Pedido' da planilha
   - Salvar os itens na aba 'ItensPedido'
   - Limpar o carrinho automaticamente
4. Uma mensagem de sucesso aparecerá com o ID do pedido
""")

# ====================================================================
# RESULTADO NA PLANILHA
# ====================================================================
print("\n" + "=" * 70)
print("RESULTADO NA PLANILHA")
print("=" * 70)
print("""
Aba 'Pedido' terá:
- pedido_id: ID único (ex: 'a1b2c3d4')
- data: Data e hora do pedido
- cliente: '38 - ABRINQ' (exemplo)
- supervisora: (vazio, pode ser preenchido depois)
- status: 'Aguardando aprovação'
- total_pedido: Valor total calculado

Aba 'ItensPedido' terá (para cada produto):
- pedido_id: Mesmo ID do pedido
- codigo: Código do produto (productCode)
- produto: Nome do produto
- qtd: Quantidade solicitada
- valor_unit: Preço unitário
- total_item: Qtd × Preço
""")

# ====================================================================
# CAMPOS CONFORME ESPECIFICAÇÃO
# ====================================================================
print("\n" + "=" * 70)
print("MAPEAMENTO DOS CAMPOS (CONFORME ESPECIFICAÇÃO)")
print("=" * 70)
print("""
CódClienteImpakto = 208831 (FIXO)
CódProImpakto = productCode (da Aba Produto)
Item = name (da Aba Produto)
Qtde = Número digitado pelo usuário
$ Unitário = price (da Aba Produtos)
$ Total = Qtde × $ Unitário
Setor = CódUnidade (da Aba Setor)
SETOR2 = items__description (da Aba Setor)
""")

# ====================================================================
# EXEMPLO PRÁTICO
# ====================================================================
print("\n" + "=" * 70)
print("EXEMPLO PRÁTICO")
print("=" * 70)
print("""
CENÁRIO: Fazer pedido de material de escritório para ABRINQ

1. ✅ Carregar planilha 'Cópia_de_Sync_Produtos.xlsx'
2. ✅ Selecionar setor: '38 - ABRINQ'
3. ✅ Buscar 'caneta' → Selecionar 'Caneta Azul'
4. ✅ Definir quantidade: 50
5. ✅ Adicionar ao pedido
6. ✅ Buscar 'papel' → Selecionar 'Papel A4'
7. ✅ Definir quantidade: 10
8. ✅ Adicionar ao pedido
9. ✅ Revisar carrinho (2 itens, total calculado)
10. ✅ Gerar Pedido e Salvar

RESULTADO:
- Pedido ID: a1b2c3d4 (exemplo)
- Total: R$ 285,00 (exemplo)
- 2 itens salvos
- Status: Aguardando aprovação
""")

# ====================================================================
# DICAS
# ====================================================================
print("\n" + "=" * 70)
print("DICAS E BOAS PRÁTICAS")
print("=" * 70)
print("""
✓ Sempre feche a planilha Excel antes de gerar o pedido
✓ Use a busca para encontrar produtos rapidamente
✓ Confira o total antes de finalizar
✓ Mantenha backups da planilha original
✓ Os pedidos ficam registrados permanentemente
✓ Você pode abrir a planilha depois para revisar
""")

print("\n" + "=" * 70)
print("PRONTO PARA USAR!")
print("=" * 70)
print("\nExecute: python3 sistema_pedidos.py\n")
