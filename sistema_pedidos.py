#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestão de Pedidos
Gerencia pedidos de produtos por setor/cliente
(Arquivo legado - compatível com Streamlit)
"""

# import tkinter as tk
# from tkinter import ttk, messagebox, filedialog
import pandas as pd
from datetime import datetime
import uuid
import os
import sys
import subprocess
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

class SistemaPedidos:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestão de Pedidos")
        self.root.geometry("1200x700")
        
        # Variáveis
        self.arquivo_excel = None
        self.df_produtos = None
        self.df_setor = None
        self.df_pedido = None
        self.df_aguardando = None
        self.itens_carrinho = []
        
        # Cliente fixo conforme especificado
        self.cod_cliente_impakto = 208831
        
        self.criar_interface()
        
    def criar_interface(self):
        """Cria a interface gráfica"""
        # Frame superior - Carregar arquivo
        frame_arquivo = ttk.LabelFrame(self.root, text="1. Carregar Planilha", padding=10)
        frame_arquivo.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_arquivo, text="📁 Selecionar Arquivo Excel", 
                   command=self.carregar_arquivo).pack(side="left", padx=5)
        self.label_arquivo = ttk.Label(frame_arquivo, text="Nenhum arquivo carregado")
        self.label_arquivo.pack(side="left", padx=10)
        
        # Notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Aba 1: Novo Pedido
        self.frame_novo_pedido = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_novo_pedido, text="➡️ Novo Pedido")
        
        # Aba 2: Pedidos Aguardando Aprovação
        self.frame_aguardando = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_aguardando, text="⏳ Aguardando Aprovação")
        
        self.criar_aba_novo_pedido()
        self.criar_aba_aguardando()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Aguardando arquivo...", 
                                    relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
    
    def criar_aba_novo_pedido(self):
        """Cria a interface da aba de novo pedido"""
        # Frame principal dividido em 2 colunas
        frame_principal = ttk.Frame(self.frame_novo_pedido)
        frame_principal.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Coluna esquerda - Seleção
        frame_esquerda = ttk.Frame(frame_principal)
        frame_esquerda.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Frame Setor/Cliente
        frame_setor = ttk.LabelFrame(frame_esquerda, text="2. Selecionar Setor/Cliente", padding=10)
        frame_setor.pack(fill="x", pady=5)
        
        ttk.Label(frame_setor, text="Setor:").grid(row=0, column=0, sticky="w", pady=2)
        self.combo_setor = ttk.Combobox(frame_setor, width=50)
        self.combo_setor.grid(row=0, column=1, pady=2, padx=5, sticky="ew")
        self.combo_setor.bind('<KeyRelease>', self.filtrar_setores)
        frame_setor.columnconfigure(1, weight=1)
        
        # Lista completa de setores para filtragem
        self.setores_completos = []
        
        # Frame Produtos
        frame_produtos = ttk.LabelFrame(frame_esquerda, text="3. Adicionar Produtos", padding=10)
        frame_produtos.pack(fill="both", expand=True, pady=5)
        
        # Filtro de produtos
        frame_filtro = ttk.Frame(frame_produtos)
        frame_filtro.pack(fill="x", pady=(0, 5))
        
        ttk.Label(frame_filtro, text="Buscar:").pack(side="left", padx=(0, 5))
        self.entry_busca = ttk.Entry(frame_filtro, width=40)
        self.entry_busca.pack(side="left", fill="x", expand=True)
        self.entry_busca.bind("<KeyRelease>", self.filtrar_produtos)
        
        # Lista de produtos
        frame_lista_produtos = ttk.Frame(frame_produtos)
        frame_lista_produtos.pack(fill="both", expand=True)
        
        scrollbar_produtos = ttk.Scrollbar(frame_lista_produtos)
        scrollbar_produtos.pack(side="right", fill="y")
        
        self.tree_produtos = ttk.Treeview(frame_lista_produtos, 
                                          columns=("codigo", "nome", "preco"),
                                          show="headings",
                                          yscrollcommand=scrollbar_produtos.set)
        scrollbar_produtos.config(command=self.tree_produtos.yview)
        
        self.tree_produtos.heading("codigo", text="Código")
        self.tree_produtos.heading("nome", text="Produto")
        self.tree_produtos.heading("preco", text="Preço Unit.")
        
        self.tree_produtos.column("codigo", width=100)
        self.tree_produtos.column("nome", width=300)
        self.tree_produtos.column("preco", width=100)
        
        self.tree_produtos.pack(fill="both", expand=True)
        self.tree_produtos.bind("<Double-1>", self.adicionar_produto_duplo_clique)
        
        # Frame quantidade e adicionar
        frame_add = ttk.Frame(frame_produtos)
        frame_add.pack(fill="x", pady=(5, 0))
        
        ttk.Label(frame_add, text="Quantidade:").pack(side="left", padx=(0, 5))
        self.spin_quantidade = ttk.Spinbox(frame_add, from_=1, to=9999, width=10)
        self.spin_quantidade.set(1)
        self.spin_quantidade.pack(side="left", padx=(0, 5))
        
        ttk.Button(frame_add, text="➕ Adicionar ao Pedido", 
                   command=self.adicionar_produto).pack(side="left", padx=5)
        
        # Coluna direita - Carrinho
        frame_direita = ttk.Frame(frame_principal)
        frame_direita.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Frame Carrinho
        frame_carrinho = ttk.LabelFrame(frame_direita, text="4. Itens do Pedido", padding=10)
        frame_carrinho.pack(fill="both", expand=True)
        
        # Tabela do carrinho
        frame_tabela_carrinho = ttk.Frame(frame_carrinho)
        frame_tabela_carrinho.pack(fill="both", expand=True)
        
        scrollbar_carrinho = ttk.Scrollbar(frame_tabela_carrinho)
        scrollbar_carrinho.pack(side="right", fill="y")
        
        self.tree_carrinho = ttk.Treeview(frame_tabela_carrinho,
                                          columns=("codigo", "item", "qtd", "preco_unit", "total"),
                                          show="headings",
                                          yscrollcommand=scrollbar_carrinho.set)
        scrollbar_carrinho.config(command=self.tree_carrinho.yview)
        
        self.tree_carrinho.heading("codigo", text="Código")
        self.tree_carrinho.heading("item", text="Item")
        self.tree_carrinho.heading("qtd", text="Qtd")
        self.tree_carrinho.heading("preco_unit", text="$ Unit.")
        self.tree_carrinho.heading("total", text="$ Total")
        
        self.tree_carrinho.column("codigo", width=80)
        self.tree_carrinho.column("item", width=200)
        self.tree_carrinho.column("qtd", width=60)
        self.tree_carrinho.column("preco_unit", width=80)
        self.tree_carrinho.column("total", width=100)
        
        self.tree_carrinho.pack(fill="both", expand=True)
        
        # Bind duplo-clique para editar quantidade
        self.tree_carrinho.bind("<Double-Button-1>", self.editar_quantidade_item)
        
        # Botões do carrinho
        frame_btn_carrinho = ttk.Frame(frame_carrinho)
        frame_btn_carrinho.pack(fill="x", pady=(5, 0))
        
        ttk.Button(frame_btn_carrinho, text="🗑️ Remover Item", 
                   command=self.remover_item).pack(side="left", padx=5)
        ttk.Button(frame_btn_carrinho, text="🗑️ Limpar Tudo", 
                   command=self.limpar_carrinho).pack(side="left", padx=5)
        
        # Frame Total e Finalizar
        frame_total = ttk.LabelFrame(frame_direita, text="5. Finalizar Pedido", padding=10)
        frame_total.pack(fill="x", pady=(5, 0))
        
        self.label_total = ttk.Label(frame_total, text="Total do Pedido: R$ 0,00", 
                                      font=("Arial", 12, "bold"))
        self.label_total.pack(pady=5)
        
        ttk.Button(frame_total, text="📝 Gerar Prévia PDF", 
                   command=self.gerar_previa_pdf).pack(pady=2, fill="x")
        
        ttk.Button(frame_total, text="💾 Salvar e Ir p/ Aguardando", 
                   command=self.salvar_e_ir_aguardando,
                   style="Accent.TButton").pack(pady=2, fill="x")
        
        ttk.Button(frame_total, text="✅ Aprovar e Finalizar Direto", 
                   command=self.gerar_pedido_direto).pack(pady=2, fill="x")
    
    def criar_aba_aguardando(self):
        """Cria a interface da aba de pedidos aguardando aprovação"""
        frame_principal = ttk.Frame(self.frame_aguardando)
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        ttk.Label(frame_principal, text="Pedidos Aguardando Aprovação", 
                  font=("Arial", 14, "bold")).pack(pady=(0, 10))
        
        # Frame de busca/filtro
        frame_busca = ttk.LabelFrame(frame_principal, text="🔍 Filtrar por Setor", padding=10)
        frame_busca.pack(fill="x", pady=(0, 10))
        
        ttk.Label(frame_busca, text="Buscar:").pack(side="left", padx=(0, 5))
        
        self.entry_filtro_setor = ttk.Entry(frame_busca, width=40)
        self.entry_filtro_setor.pack(side="left", padx=5)
        self.entry_filtro_setor.bind('<KeyRelease>', self.filtrar_aguardando)
        
        ttk.Button(frame_busca, text="❌ Limpar Filtro", 
                   command=self.limpar_filtro_aguardando).pack(side="left", padx=5)
        
        self.label_total_itens = ttk.Label(frame_busca, text="")
        self.label_total_itens.pack(side="right", padx=10)
        
        # Frame da tabela
        frame_tabela = ttk.Frame(frame_principal)
        frame_tabela.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame_tabela)
        scrollbar.pack(side="right", fill="y")
        
        self.tree_aguardando = ttk.Treeview(frame_tabela,
                                            columns=("cod_cliente", "cod_produto", "item", "qtde", 
                                                    "valor_unit", "total", "setor", "setor2"),
                                            show="headings",
                                            yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree_aguardando.yview)
        
        self.tree_aguardando.heading("cod_cliente", text="Cód Cliente")
        self.tree_aguardando.heading("cod_produto", text="Cód Produto")
        self.tree_aguardando.heading("item", text="Item")
        self.tree_aguardando.heading("qtde", text="Qtde")
        self.tree_aguardando.heading("valor_unit", text="$ Unit.")
        self.tree_aguardando.heading("total", text="$ Total")
        self.tree_aguardando.heading("setor", text="Setor")
        self.tree_aguardando.heading("setor2", text="Descrição")
        
        self.tree_aguardando.column("cod_cliente", width=80)
        self.tree_aguardando.column("cod_produto", width=90)
        self.tree_aguardando.column("item", width=200)
        self.tree_aguardando.column("qtde", width=60)
        self.tree_aguardando.column("valor_unit", width=80)
        self.tree_aguardando.column("total", width=80)
        self.tree_aguardando.column("setor", width=60)
        self.tree_aguardando.column("setor2", width=150)
        
        self.tree_aguardando.pack(fill="both", expand=True)
        
        # Botões
        frame_botoes = ttk.Frame(frame_principal)
        frame_botoes.pack(fill="x", pady=(10, 0))
        
        ttk.Button(frame_botoes, text="🔄 Atualizar Lista", 
                   command=self.carregar_pedidos_aguardando).pack(side="left", padx=5)
        
        ttk.Button(frame_botoes, text="✅ Aprovar Pedido(s)", 
                   command=self.aprovar_pedido,
                   style="Accent.TButton").pack(side="left", padx=5)
        
        ttk.Button(frame_botoes, text="✏️ Editar Pedido", 
                   command=self.editar_pedido).pack(side="left", padx=5)
        
        ttk.Button(frame_botoes, text="🗑️ Excluir Pedido", 
                   command=self.excluir_pedido_aguardando).pack(side="left", padx=5)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Aguardando arquivo...", 
                                    relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
        
    def carregar_arquivo(self):
        """Carrega o arquivo Excel"""
        arquivo = filedialog.askopenfilename(
            title="Selecionar Planilha Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not arquivo:
            return
            
        try:
            self.arquivo_excel = arquivo
            
            # Carregar as abas
            self.df_produtos = pd.read_excel(arquivo, sheet_name="Produtos")
            self.df_setor = pd.read_excel(arquivo, sheet_name="Setor")
            
            try:
                self.df_pedido = pd.read_excel(arquivo, sheet_name="Pedido")
            except:
                self.df_pedido = pd.DataFrame(columns=[
                    'CòdClienteImpakto', 'CódProImpakto', 'Item', 'Qtde', 
                    '$ Unitário', '$ Total', 'Unidade', 'Setor', 'SETOR2'
                ])
            
            try:
                self.df_aguardando = pd.read_excel(arquivo, sheet_name="Aguardando Aprovação")
            except:
                self.df_aguardando = pd.DataFrame(columns=[
                    'CòdClienteImpakto', 'CódProImpakto', 'Item', 'Qtde', 
                    '$ Unitário', '$ Total', 'Unidade', 'Setor', 'SETOR2'
                ])
            
            self.label_arquivo.config(text=f"✅ {arquivo.split('/')[-1]}")
            self.status_bar.config(text=f"Arquivo carregado: {len(self.df_produtos)} produtos, {len(self.df_setor)} setores")
            
            self.carregar_setores()
            self.carregar_produtos()
            self.carregar_pedidos_aguardando()
            
            messagebox.showinfo("Sucesso", "Arquivo carregado com sucesso!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivo:\n{str(e)}")
            
    def carregar_setores(self):
        """Carrega os setores no combobox"""
        if self.df_setor is not None:
            self.setores_completos = []
            for _, row in self.df_setor.iterrows():
                setor_texto = f"{row['CódUnidade']} - {row['items__description']}"
                self.setores_completos.append(setor_texto)
            
            self.combo_setor['values'] = self.setores_completos
            if self.setores_completos:
                self.combo_setor.set(self.setores_completos[0])
    
    def filtrar_setores(self, event=None):
        """Filtra setores baseado no texto digitado"""
        if not self.setores_completos:
            return
        
        busca = self.combo_setor.get().lower()
        
        # Se o texto está vazio, mostra todos
        if not busca:
            self.combo_setor['values'] = self.setores_completos
            return
        
        # Filtrar setores que contêm o texto
        setores_filtrados = [s for s in self.setores_completos if busca in s.lower()]
        
        self.combo_setor['values'] = setores_filtrados
                
    def carregar_produtos(self):
        """Carrega os produtos na lista"""
        if self.df_produtos is not None:
            self.tree_produtos.delete(*self.tree_produtos.get_children())
            
            for _, row in self.df_produtos.iterrows():
                preco = f"R$ {row['price']:.2f}" if pd.notna(row['price']) else "R$ 0,00"
                self.tree_produtos.insert("", "end", values=(
                    row['productCode'],
                    row['name'],
                    preco
                ), tags=(row['productCode'],))
                
    def filtrar_produtos(self, event=None):
        """Filtra produtos baseado no texto de busca"""
        if self.df_produtos is None:
            return
            
        busca = self.entry_busca.get().lower()
        self.tree_produtos.delete(*self.tree_produtos.get_children())
        
        for _, row in self.df_produtos.iterrows():
            nome = str(row['name']).lower()
            codigo = str(row['productCode']).lower()
            
            if busca in nome or busca in codigo:
                preco = f"R$ {row['price']:.2f}" if pd.notna(row['price']) else "R$ 0,00"
                self.tree_produtos.insert("", "end", values=(
                    row['productCode'],
                    row['name'],
                    preco
                ), tags=(row['productCode'],))
                
    def adicionar_produto_duplo_clique(self, event):
        """Adiciona produto ao clicar duas vezes"""
        self.adicionar_produto()
        
    def adicionar_produto(self):
        """Adiciona produto ao carrinho"""
        selecionado = self.tree_produtos.selection()
        
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um produto!")
            return
            
        if not self.combo_setor.get():
            messagebox.showwarning("Atenção", "Selecione um setor!")
            return
            
        try:
            quantidade = int(self.spin_quantidade.get())
            if quantidade <= 0:
                raise ValueError()
        except:
            messagebox.showwarning("Atenção", "Digite uma quantidade válida!")
            return
            
        # Obter dados do produto
        item = self.tree_produtos.item(selecionado[0])
        valores = item['values']
        product_code = item['tags'][0]
        
        # Buscar dados completos do produto
        produto = self.df_produtos[self.df_produtos['productCode'] == product_code].iloc[0]
        
        codigo = produto['productCode']
        nome = produto['name']
        preco = float(produto['price']) if pd.notna(produto['price']) else 0.0
        total = preco * quantidade
        
        # Adicionar ao carrinho
        self.itens_carrinho.append({
            'codigo': codigo,
            'nome': nome,
            'quantidade': quantidade,
            'preco_unitario': preco,
            'total': total
        })
        
        self.atualizar_carrinho()
        self.spin_quantidade.set(1)
        
    def atualizar_carrinho(self):
        """Atualiza a visualização do carrinho"""
        self.tree_carrinho.delete(*self.tree_carrinho.get_children())
        
        total_geral = 0
        for item in self.itens_carrinho:
            self.tree_carrinho.insert("", "end", values=(
                item['codigo'],
                item['nome'],
                item['quantidade'],
                f"R$ {item['preco_unitario']:.2f}",
                f"R$ {item['total']:.2f}"
            ))
            total_geral += item['total']
            
        self.label_total.config(text=f"Total do Pedido: R$ {total_geral:,.2f}")
        
    def editar_quantidade_item(self, event=None):
        """Edita a quantidade de um item do carrinho ao dar duplo-clique"""
        selecionado = self.tree_carrinho.selection()
        
        if not selecionado:
            return
        
        index = self.tree_carrinho.index(selecionado[0])
        item_atual = self.itens_carrinho[index]
        
        # Criar janela de diálogo
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar Quantidade")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centralizar janela
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Conteúdo
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text=f"Produto: {item_atual['nome']}", 
                  wraplength=300).pack(pady=(0, 10))
        
        frame_qtd = ttk.Frame(frame)
        frame_qtd.pack(pady=10)
        
        ttk.Label(frame_qtd, text="Nova Quantidade:").pack(side="left", padx=(0, 10))
        
        spin_nova_qtd = ttk.Spinbox(frame_qtd, from_=1, to=9999, width=10)
        spin_nova_qtd.set(item_atual['quantidade'])
        spin_nova_qtd.pack(side="left")
        spin_nova_qtd.focus()
        
        def salvar_quantidade():
            try:
                nova_qtd = int(spin_nova_qtd.get())
                if nova_qtd < 1:
                    messagebox.showerror("Erro", "Quantidade deve ser maior que zero!")
                    return
                
                # Atualizar item
                self.itens_carrinho[index]['quantidade'] = nova_qtd
                self.itens_carrinho[index]['total'] = nova_qtd * item_atual['preco_unitario']
                
                self.atualizar_carrinho()
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Erro", "Digite um número válido!")
        
        # Botões
        frame_botoes = ttk.Frame(frame)
        frame_botoes.pack(pady=(10, 0))
        
        ttk.Button(frame_botoes, text="✅ Salvar", 
                   command=salvar_quantidade).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="❌ Cancelar", 
                   command=dialog.destroy).pack(side="left", padx=5)
        
        # Enter para salvar
        spin_nova_qtd.bind("<Return>", lambda e: salvar_quantidade())
    
    def remover_item(self):
        """Remove item selecionado do carrinho"""
        selecionado = self.tree_carrinho.selection()
        
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um item para remover!")
            return
            
        item = self.tree_carrinho.item(selecionado[0])
        index = self.tree_carrinho.index(selecionado[0])
        
        self.itens_carrinho.pop(index)
        self.atualizar_carrinho()
        
    def limpar_carrinho(self):
        """Limpa todos os itens do carrinho"""
        if not self.itens_carrinho:
            return
            
        if messagebox.askyesno("Confirmar", "Deseja limpar todos os itens do carrinho?"):
            self.itens_carrinho.clear()
            self.atualizar_carrinho()
    
    def gerar_previa_pdf(self):
        """Gera prévia do pedido em PDF"""
        if not self.itens_carrinho:
            messagebox.showwarning("Atenção", "Adicione itens ao pedido!")
            return
            
        if not self.combo_setor.get():
            messagebox.showwarning("Atenção", "Selecione um setor!")
            return
        
        try:
            # Obter dados do setor
            setor_selecionado = self.combo_setor.get()
            cod_unidade = int(setor_selecionado.split(" - ")[0])
            setor_desc = setor_selecionado.split(" - ")[1]
            
            # Calcular total
            total_pedido = sum(item['total'] for item in self.itens_carrinho)
            
            # Nome do arquivo PDF
            data_arquivo = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_pdf = f"PREVIA_Pedido_{setor_desc}_{data_arquivo}.pdf"
            
            # Definir pasta de destino para os PDFs
            pasta_pdfs = r"G:\Meu Drive\projeto_atendimento\PRODUTOS PEDIDO\Pedidos Previa"
            
            # Criar a pasta se não existir
            if not os.path.exists(pasta_pdfs):
                os.makedirs(pasta_pdfs)
            
            caminho_pdf = os.path.join(pasta_pdfs, nome_pdf)
            
            # Criar PDF
            doc = SimpleDocTemplate(caminho_pdf, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            style_titulo = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            elements.append(Paragraph("<b>PRÉVIA DE PEDIDO - IMPAKTO</b>", style_titulo))
            elements.append(Spacer(1, 0.5*cm))
            
            # Informações do pedido
            info_data = [
                ['Data:', datetime.now().strftime("%d/%m/%Y %H:%M")],
                ['Cliente:', f"{self.cod_cliente_impakto}"],
                ['Setor:', f"{cod_unidade} - {setor_desc}"],
                ['Total de Itens:', f"{len(self.itens_carrinho)}"]
            ]
            
            info_table = Table(info_data, colWidths=[4*cm, 12*cm])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.8*cm))
            
            # Tabela de produtos
            data = [['Código', 'Produto', 'Qtde', 'Valor Unit.', 'Total']]
            
            for item in self.itens_carrinho:
                data.append([
                    str(item['codigo']),
                    item['nome'][:40],  # Limitar tamanho do nome
                    str(item['quantidade']),
                    f"R$ {item['preco_unitario']:.2f}",
                    f"R$ {item['total']:.2f}"
                ])
            
            # Linha de total
            data.append(['', '', '', 'TOTAL:', f"R$ {total_pedido:.2f}"])
            
            table = Table(data, colWidths=[2.5*cm, 8*cm, 2*cm, 3*cm, 3*cm])
            table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Conteúdo
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F2F2F2')]),
                
                # Linha de total
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 11),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E7E6E6')),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 1*cm))
            
            # Nota
            nota_style = ParagraphStyle(
                'Nota',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER
            )
            elements.append(Paragraph(
                "<i>Este é um documento de prévia. Para finalizar o pedido, clique em 'Finalizar e Salvar Pedido'.</i>",
                nota_style
            ))
            
            # Construir PDF
            doc.build(elements)
            
            # Abrir o PDF
            if os.name == 'nt':  # Windows
                os.startfile(caminho_pdf)
            elif os.name == 'posix':  # macOS e Linux
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', caminho_pdf])
            
            messagebox.showinfo("Sucesso", 
                f"Prévia gerada com sucesso!\n\n"
                f"Arquivo: {nome_pdf}\n\n"
                f"Revise o pedido e clique em 'Finalizar e Salvar Pedido' para confirmar.")
            
            self.status_bar.config(text=f"Prévia PDF gerada: {nome_pdf}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar prévia PDF:\n{str(e)}")
    
    def salvar_e_ir_aguardando(self):
        """Salva o pedido na aba 'Aguardando Aprovação' e vai para essa aba"""
        if not self.itens_carrinho:
            messagebox.showwarning("Atenção", "Adicione itens ao pedido!")
            return
            
        if not self.combo_setor.get():
            messagebox.showwarning("Atenção", "Selecione um setor!")
            return
            
        try:
            # Obter dados do setor
            setor_selecionado = self.combo_setor.get()
            cod_unidade = int(setor_selecionado.split(" - ")[0])
            setor_desc = setor_selecionado.split(" - ")[1]
            
            # Calcular total
            total_pedido = sum(item['total'] for item in self.itens_carrinho)
            
            # Adicionar cada item do carrinho como uma linha na aba "Aguardando Aprovação"
            for item in self.itens_carrinho:
                novo_item = pd.DataFrame([{
                    'CòdClienteImpakto': self.cod_cliente_impakto,  # Fixo: 208831
                    'CódProImpakto': item['codigo'],  # productCode
                    'Item': item['nome'],  # name
                    'Qtde': item['quantidade'],  # quantidade inserida
                    '$ Unitário': item['preco_unitario'],  # price
                    '$ Total': item['total'],  # Qtde x $ Unitário
                    'Unidade': cod_unidade,  # CódUnidade
                    'Setor': cod_unidade,  # CódUnidade
                    'SETOR2': setor_desc  # items__description
                }])
                
                self.df_aguardando = pd.concat([self.df_aguardando, novo_item], ignore_index=True)
            
            # Salvar no Excel
            try:
                with pd.ExcelWriter(self.arquivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    self.df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
                    self.df_setor.to_excel(writer, sheet_name='Setor', index=False)
                    self.df_aguardando.to_excel(writer, sheet_name='Aguardando Aprovação', index=False)
                    self.df_pedido.to_excel(writer, sheet_name='Pedido', index=False)
            except PermissionError:
                messagebox.showerror("Erro", 
                    "Arquivo Excel está aberto!\n\n"
                    "Feche o arquivo Excel e tente novamente.")
                return
            
            # Recarregar a aba Aguardando Aprovação do arquivo para garantir sincronização
            self.df_aguardando = pd.read_excel(self.arquivo_excel, sheet_name='Aguardando Aprovação')
            
            # Limpar carrinho
            self.itens_carrinho.clear()
            self.atualizar_carrinho()
            
            # Atualizar lista de aguardando
            self.carregar_pedidos_aguardando()
            
            # Ir para aba Aguardando Aprovação
            self.notebook.select(1)
            
            messagebox.showinfo("Sucesso", 
                f"Pedido salvo em 'Aguardando Aprovação'!\n\n"
                f"Total: R$ {total_pedido:,.2f}\n"
                f"Itens: {len(self.itens_carrinho)}")
            
            self.status_bar.config(text=f"Pedido salvo em 'Aguardando Aprovação'!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar pedido:\n{str(e)}")
    
    def gerar_pedido_direto(self):
        """Aprova e finaliza pedido direto na aba Pedido"""
        if not self.itens_carrinho:
            messagebox.showwarning("Atenção", "Adicione itens ao pedido!")
            return
            
        if not self.combo_setor.get():
            messagebox.showwarning("Atenção", "Selecione um setor!")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                    "Deseja aprovar e finalizar este pedido diretamente?\n\n"
                                    "O pedido será salvo direto na aba 'Pedido'."):
            return
            
        try:
            # Obter dados do setor
            setor_selecionado = self.combo_setor.get()
            cod_unidade = int(setor_selecionado.split(" - ")[0])
            setor_desc = setor_selecionado.split(" - ")[1]
            
            # Calcular total
            total_pedido = sum(item['total'] for item in self.itens_carrinho)
            
            # Adicionar cada item do carrinho como uma linha na aba "Pedido"
            for item in self.itens_carrinho:
                novo_item = pd.DataFrame([{
                    'CòdClienteImpakto': self.cod_cliente_impakto,  # Fixo: 208831
                    'CódProImpakto': item['codigo'],  # productCode
                    'Item': item['nome'],  # name
                    'Qtde': item['quantidade'],  # quantidade inserida
                    '$ Unitário': item['preco_unitario'],  # price
                    '$ Total': item['total'],  # Qtde x $ Unitário
                    'Unidade': cod_unidade,  # CódUnidade
                    'Setor': cod_unidade,  # CódUnidade
                    'SETOR2': setor_desc  # items__description
                }])
                
                self.df_pedido = pd.concat([self.df_pedido, novo_item], ignore_index=True)
            
            # Salvar no Excel
            try:
                with pd.ExcelWriter(self.arquivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    self.df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
                    self.df_setor.to_excel(writer, sheet_name='Setor', index=False)
                    self.df_aguardando.to_excel(writer, sheet_name='Aguardando Aprovação', index=False)
                    self.df_pedido.to_excel(writer, sheet_name='Pedido', index=False)
            except PermissionError:
                messagebox.showerror("Erro", 
                    "Arquivo Excel está aberto!\n\n"
                    "Feche o arquivo Excel e tente novamente.")
                return
            
            # Recarregar a aba Pedido
            self.df_pedido = pd.read_excel(self.arquivo_excel, sheet_name='Pedido')
            
            messagebox.showinfo("Sucesso", 
                f"Pedido aprovado e salvo em 'Pedido'!\n\n"
                f"Total: R$ {total_pedido:,.2f}\n"
                f"Itens: {len(self.itens_carrinho)}\n"
                f"Setor: {setor_desc}")
            
            # Limpar carrinho
            self.itens_carrinho.clear()
            self.atualizar_carrinho()
            
            self.status_bar.config(text=f"Pedido aprovado e salvo!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar pedido:\n{str(e)}")
    
    def carregar_pedidos_aguardando(self):
        """Carrega pedidos aguardando aprovação na tabela"""
        if self.df_aguardando is None:
            return
        
        self.tree_aguardando.delete(*self.tree_aguardando.get_children())
        
        if len(self.df_aguardando) == 0:
            self.label_total_itens.config(text="Total: 0 itens")
            return
        
        # Obter filtro se existir
        filtro_texto = ""
        if hasattr(self, 'entry_filtro_setor'):
            filtro_texto = self.entry_filtro_setor.get().strip().lower()
        
        contador = 0
        for _, row in self.df_aguardando.iterrows():
            try:
                setor2 = str(row['SETOR2']).lower()
                
                # Aplicar filtro se houver texto de busca
                if filtro_texto and filtro_texto not in setor2:
                    continue
                
                self.tree_aguardando.insert("", "end", values=(
                    int(row['CòdClienteImpakto']),
                    row['CódProImpakto'],
                    row['Item'],
                    int(row['Qtde']),
                    f"R$ {float(row['$ Unitário']):.2f}",
                    f"R$ {float(row['$ Total']):.2f}",
                    int(row['Setor']),
                    row['SETOR2']
                ))
                contador += 1
            except Exception as e:
                print(f"Erro ao carregar linha: {e}")
                continue
        
        # Atualizar contador
        if hasattr(self, 'label_total_itens'):
            if filtro_texto:
                self.label_total_itens.config(text=f"Mostrando: {contador} de {len(self.df_aguardando)} itens")
            else:
                self.label_total_itens.config(text=f"Total: {contador} itens")
    
    def filtrar_aguardando(self, event=None):
        """Filtra a lista de pedidos aguardando pelo nome do setor"""
        self.carregar_pedidos_aguardando()
    
    def limpar_filtro_aguardando(self):
        """Limpa o filtro e mostra todos os pedidos"""
        if hasattr(self, 'entry_filtro_setor'):
            self.entry_filtro_setor.delete(0, tk.END)
            self.carregar_pedidos_aguardando()
    
    def aprovar_pedido(self):
        """Aprova pedidos selecionados e move para aba Pedido"""
        selecionados = self.tree_aguardando.selection()
        
        if not selecionados:
            messagebox.showwarning("Atenção", "Selecione pelo menos um pedido para aprovar!")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                    f"Deseja aprovar {len(selecionados)} item(ns) selecionado(s)?"):
            return
        
        try:
            # Obter índices dos itens selecionados
            indices_remover = []
            for item in selecionados:
                index = self.tree_aguardando.index(item)
                indices_remover.append(index)
                
                # Adicionar à aba Pedido
                row_data = self.df_aguardando.iloc[index]
                novo_pedido = pd.DataFrame([row_data])
                self.df_pedido = pd.concat([self.df_pedido, novo_pedido], ignore_index=True)
            
            # Remover da aba Aguardando (em ordem reversa para não afetar índices)
            for index in sorted(indices_remover, reverse=True):
                self.df_aguardando = self.df_aguardando.drop(self.df_aguardando.index[index]).reset_index(drop=True)
            
            # Salvar no Excel
            with pd.ExcelWriter(self.arquivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                self.df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
                self.df_setor.to_excel(writer, sheet_name='Setor', index=False)
                self.df_aguardando.to_excel(writer, sheet_name='Aguardando Aprovação', index=False)
                self.df_pedido.to_excel(writer, sheet_name='Pedido', index=False)
            
            messagebox.showinfo("Sucesso", f"{len(selecionados)} item(ns) aprovado(s) e movido(s) para 'Pedido'!")
            
            # Atualizar lista
            self.carregar_pedidos_aguardando()
            self.status_bar.config(text=f"{len(selecionados)} pedido(s) aprovado(s)!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aprovar pedido:\n{str(e)}")
    
    def editar_pedido(self):
        """Carrega pedido selecionado no carrinho para edição"""
        selecionados = self.tree_aguardando.selection()
        
        if not selecionados:
            messagebox.showwarning("Atenção", "Selecione um pedido para editar!")
            return
        
        if len(selecionados) > 1:
            messagebox.showwarning("Atenção", "Selecione apenas um pedido para editar!")
            return
        
        try:
            index = self.tree_aguardando.index(selecionados[0])
            
            # Limpar carrinho atual
            self.itens_carrinho.clear()
            
            # Buscar todas as linhas do mesmo setor na aguardando
            row_selecionada = self.df_aguardando.iloc[index]
            setor = row_selecionada['Setor']
            setor2 = row_selecionada['SETOR2']
            
            # Filtrar itens do mesmo setor
            indices_mesmo_pedido = []
            for idx, row in self.df_aguardando.iterrows():
                if row['Setor'] == setor and row['SETOR2'] == setor2:
                    # Adicionar ao carrinho
                    self.itens_carrinho.append({
                        'codigo': row['CódProImpakto'],
                        'nome': row['Item'],
                        'quantidade': int(row['Qtde']),
                        'preco_unitario': float(row['$ Unitário']),
                        'total': float(row['$ Total'])
                    })
                    indices_mesmo_pedido.append(idx)
            
            # Remover do DataFrame de aguardando
            self.df_aguardando = self.df_aguardando.drop(indices_mesmo_pedido).reset_index(drop=True)
            
            # Selecionar o setor no combo (com fallback para garantir que funcione)
            setor_int = int(setor) if not isinstance(setor, int) else setor
            setor_texto = f"{setor_int} - {setor2}"
            
            setor_encontrado = False
            combo_values = self.combo_setor['values']
            
            for i, valor in enumerate(combo_values):
                # Comparar com várias possibilidades
                if (valor == setor_texto or 
                    valor.startswith(f"{setor_int} -") or
                    str(setor_int) in valor.split('-')[0].strip()):
                    self.combo_setor.current(i)
                    setor_encontrado = True
                    break
            
            # Se não encontrou, tentar definir o valor diretamente
            if not setor_encontrado:
                self.combo_setor.set(setor_texto)
            
            # Atualizar carrinho
            self.atualizar_carrinho()
            
            # Salvar mudanças
            with pd.ExcelWriter(self.arquivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                self.df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
                self.df_setor.to_excel(writer, sheet_name='Setor', index=False)
                self.df_aguardando.to_excel(writer, sheet_name='Aguardando Aprovação', index=False)
                self.df_pedido.to_excel(writer, sheet_name='Pedido', index=False)
            
            # Atualizar lista e ir para aba de novo pedido
            self.carregar_pedidos_aguardando()
            self.notebook.select(0)  # Ir para aba "Novo Pedido"
            
            messagebox.showinfo("Sucesso", 
                                f"Pedido carregado para edição!\n\n"
                                f"Faça as alterações necessárias e clique em 'Finalizar e Salvar Pedido'.")
            
            self.status_bar.config(text="Pedido carregado para edição")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao editar pedido:\n{str(e)}")
    
    def excluir_pedido_aguardando(self):
        """Exclui pedido(s) selecionado(s) da lista de aguardando"""
        selecionados = self.tree_aguardando.selection()
        
        if not selecionados:
            messagebox.showwarning("Atenção", "Selecione pelo menos um pedido para excluir!")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                    f"Deseja excluir {len(selecionados)} item(ns) selecionado(s)?"):
            return
        
        try:
            # Obter índices dos itens selecionados
            indices_remover = []
            for item in selecionados:
                index = self.tree_aguardando.index(item)
                indices_remover.append(index)
            
            # Remover (em ordem reversa)
            for index in sorted(indices_remover, reverse=True):
                self.df_aguardando = self.df_aguardando.drop(self.df_aguardando.index[index]).reset_index(drop=True)
            
            # Salvar no Excel
            with pd.ExcelWriter(self.arquivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                self.df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
                self.df_setor.to_excel(writer, sheet_name='Setor', index=False)
                self.df_aguardando.to_excel(writer, sheet_name='Aguardando Aprovação', index=False)
                self.df_pedido.to_excel(writer, sheet_name='Pedido', index=False)
            
            messagebox.showinfo("Sucesso", f"{len(selecionados)} item(ns) excluído(s)!")
            
            # Atualizar lista
            self.carregar_pedidos_aguardando()
            self.status_bar.config(text=f"{len(selecionados)} pedido(s) excluído(s)!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao excluir pedido:\n{str(e)}")


def main():
    """Função principal"""
    root = tk.Tk()
    app = SistemaPedidos(root)
    root.mainloop()


if __name__ == "__main__":
    main()
