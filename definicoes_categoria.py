# -*- coding: utf-8 -*-
"""
App Streamlit - Gerador de Estrutura Mercadológica Scanntech
"""
import streamlit as st
import pandas as pd
from jinja2 import Template
import base64
import requests
import io
import zipfile
import re

try:
    from weasyprint import HTML
except ImportError:
    st.error("Erro Crítico: WeasyPrint não instalado. Execute 'pip install weasyprint'.")

# --- Funções Auxiliares ---

def formatar_lista_html(texto):
    """Converte texto com marcadores da planilha em itens de lista HTML <li>."""
    if pd.isna(texto) or not str(texto).strip():
        return "<ul><li>Nenhum item cadastrado.</li></ul>"
    linhas = [linha.strip().lstrip('•').lstrip('-').strip() for linha in str(texto).split('\n') if linha.strip()]
    return "<ul>" + "".join(f"<li>{linha}</li>" for linha in linhas) + "</ul>"

def baixar_imagem_base64(url):
    """
    Tenta baixar uma imagem da web e convertê-la para Base64 embutido.
    Retorna vazio se falhar ou se não houver URL, garantindo resiliência.
    """
    if pd.isna(url) or not str(url).strip():
        return ""
    
    url = str(url).strip()
    
    # Se já for um arquivo local ou base64 na planilha, retorna como está
    if not url.startswith('http'):
        return url 

    try:
        # Timeout de 5s para não travar o loop inteiro se um link estiver morto
        resposta = requests.get(url, timeout=5) 
        if resposta.status_code == 200:
            tipo_conteudo = resposta.headers.get('content-type', 'image/png')
            b64 = base64.b64encode(resposta.content).decode('utf-8')
            return f"data:{tipo_conteudo};base64,{b64}"
        else:
            return ""
    except Exception:
        return "" # Retorna vazio caso o servidor da imagem rejeite a conexão

def arquivo_para_base64(arquivo_upload):
    """Lê um st.file_uploader file_object e transforma em string Base64."""
    if arquivo_upload is not None:
        b64 = base64.b64encode(arquivo_upload.read()).decode('utf-8')
        # Determina o mimetype grosseiramente pela extensão
        ext = arquivo_upload.name.split('.')[-1].lower()
        mimetype = "image/png" if ext == "png" else "image/jpeg"
        return f"data:{mimetype};base64,{b64}"
    return ""

# --- Configuração da Interface Streamlit ---

st.set_page_config(page_title="Scanntech - Gerador de Categorias", page_icon="📄", layout="wide")

st.title("Geração de Definições de Estrutura Mercadológica")
st.markdown("Automatize a criação de PDFs da Scanntech padronizando arquivos em lote utilizando o brandbook oficial.")

with st.sidebar:
    st.header("1. Upload de Ativos Base")
    upload_planilha = st.file_uploader("Planilha de Dados (.xlsx)", type=["xlsx"])
    upload_html = st.file_uploader("Template HTML Oficial", type=["html"])
    
    st.markdown("---")
    st.header("2. Identidade Visual")
    upload_logo = st.file_uploader("Logo Preferencial (PNG)", type=["png", "jpg"])
    upload_grafismo = st.file_uploader("Grafismo Topo (PNG)", type=["png", "jpg"])

# --- Lógica de Processamento Principal ---

if st.button("Gerar PDFs de Categorias", type="primary"):
    
    # Validação de Arquivos
    if not upload_planilha or not upload_html:
        st.warning("⚠️ Por favor, faça o upload da Planilha e do Template HTML na barra lateral para prosseguir.")
        st.stop()
        
    if not upload_logo or not upload_grafismo:
        st.info("💡 Dica: Você não fez upload do Logo ou do Grafismo. Tentaremos usar o que já estiver no código, mas pode resultar em campos em branco.")

    with st.spinner("Lendo banco de dados e preparando ativos de imagem..."):
        # Processa os uploads visuais para a memória RAM
        logo_b64 = arquivo_para_base64(upload_logo)
        grafismo_b64 = arquivo_para_base64(upload_grafismo)
        
        # Leitura da estrutura
        df = pd.read_excel(upload_planilha)
        html_molde_original = upload_html.read().decode('utf-8')
        
        # Substituição transparente no HTML: Troca os caminhos estáticos locais
        # que estavam no seu HTML pelas imagens Base64 recém-carregadas na web
        html_preparado = html_molde_original
        if logo_b64:
            html_preparado = html_preparado.replace('id vs/Logo Scanntech Versão Preferencial.png', logo_b64)
        if grafismo_b64:
            html_preparado = html_preparado.replace('id vs/Grafismos Scanntech digital RGB - 01.png', grafismo_b64)

        jinja_template = Template(html_preparado)
        
        # Prepara o buffer de memória para criar o arquivo .zip
        zip_buffer = io.BytesIO()
        
        # Barra de Progresso Visual
        barra_progresso = st.progress(0)
        total_linhas = len(df)
        status_texto = st.empty()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for index, linha in df.iterrows():
            codigo = str(linha.get('CODIGO_CATEGORIA', f"CAT_{index}")).strip()
            nome = str(linha.get('NOME_CATEGORIA', "S_Nome")).strip()
            
            nome_seguro = "".join(char for char in nome if char.isalnum() or char in (' ', '_', '-')).rstrip()
            nome_arquivo_pdf = f"Definicao_{codigo.replace('.', '_')}_{nome_seguro}.pdf"
            
            status_texto.text(f"Processando [{index+1}/{total_linhas}]: {nome}")
            
            # Mapeamento e conversão on-the-fly de URLs em imagens embutidas Base64
            contexto = {
                "nome_categoria": nome,
                "codigo_categoria": codigo,
                "definicao": linha.get('DEFINICAO', ''),
                "padrao_contenido": linha.get('PADRAO_CONTENIDO', ''),
                "padrao_descritivo": linha.get('PADRAO_DESCRITIVO', ''),
                
                "obs_contenido": linha['OBS_CONTENIDO'] if 'OBS_CONTENIDO' in df.columns and pd.notna(linha['OBS_CONTENIDO']) else "",
                "obs_descritivo": linha['OBS_DESCRITIVO'] if 'OBS_DESCRITIVO' in df.columns and pd.notna(linha['OBS_DESCRITIVO']) else "",
                
                "produtos_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_PERTENCEM_TXT', '')),
                "produtos_nao_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_NAO_PERTENCEM_TXT', '')),
                
                # Baixa as imagens das URLs em tempo real e entrega ao HTML
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
            
            # Renderiza o Template
            html_renderizado = jinja_template.render(contexto)
            
            # Gera os bytes do PDF em memória e salva dentro do arquivo ZIP virtual
            pdf_bytes = HTML(string=html_renderizado, base_url=".").write_pdf()
            zip_file.writestr(nome_arquivo_pdf, pdf_bytes)
            
            # Atualiza barra de progresso
            barra_progresso.progress((index + 1) / total_linhas)

    # Limpeza visual e finalização
    status_texto.text("✅ Processamento concluído! Todos os PDFs empacotados e prontos para download.")
    st.balloons()
    
    # Exibe botão de Download
    zip_buffer.seek(0)
    st.download_button(
        label="⬇️ Baixar Pacote Completo (.ZIP)",
        data=zip_buffer,
        file_name="Scanntech_Categorias_Lote.zip",
        mime="application/zip",
        type="primary"
    )