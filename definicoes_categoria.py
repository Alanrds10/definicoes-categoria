# -*- coding: utf-8 -*-
"""
App Streamlit - Gerador de Estrutura Mercadológica Scanntech (Automático via Repositório)
"""
import streamlit as st
import pandas as pd
from jinja2 import Template
import base64
import requests
import io
import zipfile
import os

try:
    from weasyprint import HTML
except ImportError:
    st.error("Erro Crítico: WeasyPrint não instalado. Verifique o requirements.txt.")

# --- Funções Auxiliares ---

def formatar_lista_html(texto):
    """Converte texto com marcadores da planilha em itens de lista HTML <li>."""
    if pd.isna(texto) or not str(texto).strip():
        return "<ul><li>Nenhum item cadastrado.</li></ul>"
    linhas = [linha.strip().lstrip('•').lstrip('-').strip() for linha in str(texto).split('\n') if linha.strip()]
    return "<ul>" + "".join(f"<li>{linha}</li>" for linha in linhas) + "</ul>"

def baixar_imagem_base64(url):
    """Baixa imagem da web e converte para Base64 (ignora erros graciosamente)."""
    if pd.isna(url) or not str(url).strip():
        return ""
    url = str(url).strip()
    if not url.startswith('http'):
        return url 

    try:
        resposta = requests.get(url, timeout=5) 
        if resposta.status_code == 200:
            tipo_conteudo = resposta.headers.get('content-type', 'image/png')
            b64 = base64.b64encode(resposta.content).decode('utf-8')
            return f"data:{tipo_conteudo};base64,{b64}"
    except Exception:
        pass
    return ""

def carregar_arquivo_local_base64(caminho_arquivo):
    """Lê um arquivo do próprio repositório GitHub e converte para Base64."""
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = caminho_arquivo.split('.')[-1].lower()
            mimetype = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mimetype};base64,{b64}"
    return ""

# --- Configuração da Interface Streamlit ---

st.set_page_config(page_title="Scanntech - Gerador de Categorias", page_icon="📄", layout="wide")

st.title("Geração de Definições de Estrutura Mercadológica")
st.markdown("Faça o upload da planilha atualizada. O template e a identidade visual são carregados automaticamente do sistema.")

with st.sidebar:
    st.header("Base de Dados")
    upload_planilha = st.file_uploader("Subir Planilha (.xlsx)", type=["xlsx"])
    
    st.markdown("---")
    st.info("📌 **Ativos do Sistema:**\nO layout HTML e as imagens da marcação estão sendo puxados automaticamente da raiz do repositório.")

# --- Lógica de Processamento Principal ---

if st.button("Gerar PDFs de Categorias", type="primary"):
    
    if not upload_planilha:
        st.warning("⚠️ Faça o upload da Planilha de Dados (.xlsx) para prosseguir.")
        st.stop()

    with st.spinner("Lendo arquivos do repositório e estruturando o gerador..."):
        # 1. Busca os arquivos que já estão no seu repositório GitHub
        caminho_html = "HTML_CSS_DEFINICAO-DE-CATEGORIA.html"
        caminho_logo = "Logo Scanntech Versão Preferencial.png"
        
        # Lê o HTML oficial
        if not os.path.exists(caminho_html):
            st.error(f"Erro: O arquivo '{caminho_html}' não foi encontrado na raiz do projeto.")
            st.stop()
            
        with open(caminho_html, "r", encoding="utf-8") as f:
            html_preparado = f.read()

        # Converte a logo local em Base64 e injeta no HTML
        logo_b64 = carregar_arquivo_local_base64(caminho_logo)
        if logo_b64:
            html_preparado = html_preparado.replace('id vs/Logo Scanntech Versão Preferencial.png', logo_b64)
            # Caso a logo estivesse referenciada apenas pelo nome
            html_preparado = html_preparado.replace('Logo Scanntech Versão Preferencial.png', logo_b64)

        jinja_template = Template(html_preparado)
        df = pd.read_excel(upload_planilha)
        zip_buffer = io.BytesIO()
        
        barra_progresso = st.progress(0)
        total_linhas = len(df)
        status_texto = st.empty()

    # 2. Renderização em Lote
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for index, linha in df.iterrows():
            codigo = str(linha.get('CODIGO_CATEGORIA', f"CAT_{index}")).strip()
            nome = str(linha.get('NOME_CATEGORIA', "S_Nome")).strip()
            
            nome_seguro = "".join(char for char in nome if char.isalnum() or char in (' ', '_', '-')).rstrip()
            nome_arquivo_pdf = f"Definicao_{codigo.replace('.', '_')}_{nome_seguro}.pdf"
            
            status_texto.text(f"Processando [{index+1}/{total_linhas}]: {nome}")
            
            contexto = {
                "nome_categoria": nome,
                "codigo_categoria": codigo,
                "definicao": linha.get('DEFINICAO', ''),
                "padrao_contenido": linha.get('PADRAO_CONTENIDO', ''),
                "padrao_descritivo": linha.get('PADRAO_DESCRITIVO', ''),
                
                "produtos_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_PERTENCEM_TXT', '')),
                "produtos_nao_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_NAO_PERTENCEM_TXT', '')),
                
                # Baixa imagens das URLs
                "foto_pertence_1_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_1_PATH', '')),
                "foto_pertence_1_desc": linha.get('FOTO_PERTENCE_1_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_1_DESC')) else "",
                "foto_pertence_2_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_2_PATH', '')),
                "foto_pertence_2_desc": linha.get('FOTO_PERTENCE_2_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_2_DESC')) else "",
                "foto_pertence_3_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_3_PATH', '')),
                "foto_pertence_3_desc": linha.get('FOTO_PERTENCE_3_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_3_DESC')) else "",
                
                "foto_nao_pertence_1_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_1_PATH', '')),
                "foto_nao_pertence_1_desc": linha.get('FOTO_NAO_PERTENCE_1_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_1_DESC')) else "",
                "foto_nao_pertence_2_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_2_PATH', '')),
                "foto_nao_pertence_2_desc": linha.get('FOTO_NAO_PERTENCE_2_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_2_DESC')) else "",
                "foto_nao_pertence_3_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_3_PATH', '')),
                "foto_nao_pertence_3_desc": linha.get('FOTO_NAO_PERTENCE_3_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_3_DESC')) else "",
            }
            
            html_renderizado = jinja_template.render(contexto)
            pdf_bytes = HTML(string=html_renderizado, base_url=".").write_pdf()
            zip_file.writestr(nome_arquivo_pdf, pdf_bytes)
            
            barra_progresso.progress((index + 1) / total_linhas)

    status_texto.text("✅ Sucesso! Todas as definições foram geradas.")
    st.balloons()
    
    zip_buffer.seek(0)
    st.download_button(
        label="⬇️ Baixar Pacote Completo (.ZIP)",
        data=zip_buffer,
        file_name="Scanntech_Categorias_Lote.zip",
        mime="application/zip",
        type="primary"
    )