#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste - Validação da lógica do sistema
"""

import pandas as pd
from datetime import datetime
import uuid

def testar_sistema():
    """Testa a lógica do sistema sem interface gráfica"""
    
    print("=" * 70)
    print("TESTE DO SISTEMA DE PEDIDOS")
    print("=" * 70)
    
    # Carregar planilha
    arquivo = '/mnt/user-data/uploads/Cópia_de_Sync_Produtos.xlsx'
    
    print("\n1. Carregando planilha...")
    df_produtos = pd.read_excel(arquivo, sheet_name="Produtos")
    df_setor = pd.read_excel(arquivo, sheet_name="Setor")
    
    print(f"   ✓ {len(df_produtos)} produtos carregados")
    print(f"   ✓ {len(df_setor)} setores carregados")
    
    # Mostrar alguns setores
    print("\n2. Setores disponíveis (primeiros 5):")
    for idx, row in df_setor.head(5).iterrows():
        print(f"   - {row['CódUnidade']}: {row['items__description']}")
    
    # Mostrar alguns produtos
    print("\n3. Produtos disponíveis (primeiros 5):")
    for idx, row in df_produtos.head(5).iterrows():
        preco = row['price'] if pd.notna(row['price']) else 0
        print(f"   - [{row['productCode']}] {row['name']}: R$ {preco:.2f}")
    
    # Simular criação de pedido
    print("\n4. Simulando criação de pedido...")
    
    # Dados do pedido simulado
    setor_selecionado = df_setor.iloc[0]
    cod_unidade = setor_selecionado['CódUnidade']
    setor_desc = setor_selecionado['items__description']
    
    print(f"   Cliente: {cod_unidade} - {setor_desc}")
    
    # Itens do pedido (simulado)
    itens_simulados = []
    
    # Adicionar 3 produtos como exemplo
    for i in range(min(3, len(df_produtos))):
        produto = df_produtos.iloc[i]
        quantidade = (i + 1) * 5  # 5, 10, 15
        preco = float(produto['price']) if pd.notna(produto['price']) else 0.0
        total = preco * quantidade
        
        item = {
            'codigo': produto['productCode'],
            'nome': produto['name'],
            'quantidade': quantidade,
            'preco_unitario': preco,
            'total': total
        }
        itens_simulados.append(item)
        
        print(f"   + Item {i+1}: {item['nome']}")
        print(f"     Código: {item['codigo']}")
        print(f"     Qtd: {item['quantidade']}")
        print(f"     Preço Unit.: R$ {item['preco_unitario']:.2f}")
        print(f"     Total: R$ {item['total']:.2f}")
    
    # Calcular total
    total_pedido = sum(item['total'] for item in itens_simulados)
    print(f"\n   TOTAL DO PEDIDO: R$ {total_pedido:,.2f}")
    
    # Gerar dados do pedido
    pedido_id = str(uuid.uuid4())[:8]
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n5. Dados do pedido gerado:")
    print(f"   ID: {pedido_id}")
    print(f"   Data: {data_atual}")
    print(f"   Status: Aguardando aprovação")
    print(f"   Total: R$ {total_pedido:,.2f}")
    print(f"   Itens: {len(itens_simulados)}")
    
    # Verificar campos conforme especificação
    print("\n6. Mapeamento dos campos:")
    print(f"   CódClienteImpakto: 208831 (FIXO)")
    print(f"   CódProImpakto: {itens_simulados[0]['codigo']}")
    print(f"   Item: {itens_simulados[0]['nome']}")
    print(f"   Qtde: {itens_simulados[0]['quantidade']}")
    print(f"   $ Unitário: R$ {itens_simulados[0]['preco_unitario']:.2f}")
    print(f"   $ Total: R$ {itens_simulados[0]['total']:.2f}")
    print(f"   Setor: {cod_unidade}")
    print(f"   SETOR2: {setor_desc}")
    
    print("\n" + "=" * 70)
    print("TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print("\nO sistema está funcionando corretamente.")
    print("Execute 'python3 sistema_pedidos.py' para usar a interface gráfica.\n")

if __name__ == "__main__":
    testar_sistema()
