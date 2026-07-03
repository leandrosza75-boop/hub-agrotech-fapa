import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime

# Configuração da página para se adaptar a qualquer ecrã/tela
st.set_page_config(layout="wide", page_title="AgroGestão - Sistema Integrado de OS")

# --- 1. BANCO DE DADOS ---
def conectar_bd():
    return sqlite3.connect('gestao_agricola_avancada.db')

def criar_tabela():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id TEXT PRIMARY KEY,
            dia TEXT,
            equipe TEXT,
            trator TEXT,
            implemento TEXT,
            operador TEXT,
            periodo TEXT,
            talhao TEXT,
            atividade TEXT,
            produto TEXT,
            dosagem REAL,
            horimetro_estimado REAL,
            clima_temp REAL,
            clima_umi REAL
        )
    ''')
    conn.commit()
    conn.close()

criar_tabela()

# --- 2. CONFIGURAÇÕES E LISTAS DE CADASTRO ---
EQUIPES = ['TAOL', 'HF', 'RADAR', 'HERBOLOGIA/FISIOLOGIA', 'MELHORAMENTO', 'FERTILIDADE', 'FITOPATOLOGIA', 'MILHO/FEIJÃO']
DIAS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
TRATORES = ['CASE 80', 'TL 75', 'JOHN DEERE 5078', 'T6', 'VW CONSTELATION', '283', '292', 'VALMET']
IMPLEMENTOS = ['HALDRUP', 'ACCURA', 'CONDOR ANTIGO', 'CONDOR NOVO', 'SEMINA', 'SHM', 'SHP', 'VT 6 LINHAS', 'VT 11 LINHAS', 'LÂMINA', 'DESSECADOR DE CAMINHO']
OPERADORES = ['JEAN', 'NEORALDO', 'ADENILTON', 'VALDOMIRO', 'AUGERO']
PERIODOS = ['DIA INTEIRO', 'PRIMEIRO TURNO', 'SEGUNDO TURNO']
TALHOES = ['Talhão A1', 'Talhão A2', 'Área Experimental 01', 'Área Experimental 02', 'Baixada', 'Sede']

# --- 3. REGRAS DE VALIDAÇÃO DE SEGURANÇA ---
def validar_regras_bd(dia, equipe, trator, implemento, operador, periodo):
    if operador == "VALDOMIRO" and "CONDOR" in implemento:
        return False, "❌ Bloqueio Operacional: O operador VALDOMIRO não possui certificação para os implementos CONDOR."
        
    semeaduras = ['HALDRUP', 'SEMINA', 'SHM', 'SHP', 'VT 6 LINHAS', 'VT 11 LINHAS']
    if implemento in semeaduras and trator in ['VALMET', '283', '292']:
        return False, f"❌ Bloqueio Técnico: Semeadoras de precisão ({implemento}) exigem trator com compatibilidade hidráulica avançada (Incompatível com {trator})."
        
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT equipe, trator, implemento, operador, periodo FROM ordens_servico WHERE dia = ?", (dia,))
    registros_dia = cursor.fetchall()
    conn.close()
    
    for reg_equipe, reg_trator, reg_implemento, reg_operador, reg_periodo in registros_dia:
        choque_turno = (periodo == "DIA INTEIRO" or reg_periodo == "DIA INTEIRO" or periodo == reg_periodo)
        if choque_turno:
            if reg_trator == trator and trator != "VW CONSTELATION":
                return False, f"⚠️ Conflito de Frota: O trator {trator} já está alocado neste turno pela equipe {reg_equipe}."
            if reg_implemento == implemento:
                return False, f"⚠️ Conflito de Implemento: O implemento {implemento} já está em uso pela equipe {reg_equipe}."
            if reg_operador == operador:
                return False, f"⚠️ Conflito de Operador: O operador {operador} já está escalado na equipe {reg_equipe}."
                
    return True, "✅ Operação validada com sucesso."

# --- 4. FUNÇÕES DE PERSISTÊNCIA ---
def salvar_no_banco(d):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ordens_servico VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (d['id'], d['dia'], d['equipe'], d['trator'], d['implemento'], d['operador'], d['periodo'], 
          d['talhao'], d['atividade'], d['produto'], d['dosagem'], d['horimetro'], d['temp'], d['umi']))
    conn.commit()
    conn.close()

def carregar_dados_bd():
    conn = conectar_bd()
    df = pd.read_sql_query("SELECT * FROM ordens_servico", conn)
    conn.close()
    return df

def limpar_banco():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ordens_servico")
    conn.commit()
    conn.close()

# --- 5. EMISSÃO DE PDF SEGURO ---
def gerar_pdf_os(row):
    pdf = FPDF()
    pdf.add_page()
    
    def txt(texto):
        return str(texto).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, txt(f"ORDEM DE SERVIÇO AGRÍCOLA - {row['id']}"), ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, txt("1. LOGÍSTICA E ALOCAÇÃO"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 6, txt(f"Equipe: {row['equipe']}"), border=1)
    pdf.cell(95, 6, txt(f"Programação: {row['dia']} ({row['periodo']})"), border=1, ln=True)
    pdf.cell(95, 6, txt(f"Trator: {row['trator']}"), border=1)
    pdf.cell(95, 6, txt(f"Implemento: {row['implemento']}"), border=1, ln=True)
    pdf.cell(190, 6, txt(f"Operador Responsável: {row['operador']}"), border=1, ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, txt("2. PLANEJAMENTO DA ATIVIDADE"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 6, txt(f"Local / Talhão: {row['talhao']}"), border=1)
    pdf.cell(95, 6, txt(f"Operação: {row['atividade']}"), border=1, ln=True)
    pdf.cell(95, 6, txt(f"Estimativa de Trabalho: {row['horimetro_estimado']} Horas"), border=1)
    pdf.cell(95, 6, txt(f"Defensivo/Insumo: {row['produto']} (Dose: {row['dosagem']} L-Kg/ha)"), border=1, ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, txt("3. PARÂMETROS DE SEGURANÇA (CIPA / NR-31)"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 6, txt(f"Temperatura Máxima Limite: {row['clima_temp']} °C  |  Umidade Mínima Aceitável: {row['clima_umi']}%"), border=1, ln=True)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(190, 5, txt("Atenção: Use EPI completo durante a manipulação de insumos e calibração de equipamentos. Respeite as normas vigentes de segurança no meio rural."), border=1)
    
    pdf.ln(20)
    pdf.line(10, pdf.get_y(), 90, pdf.get_y())
    pdf.line(110, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Arial", "", 9)
    pdf.cell(80, 5, txt("Assinatura do Supervisor"), ln=False, align="C")
    pdf.cell(20, 5, "", ln=False)
    pdf.cell(80, 5, txt("Assinatura do Operador"), ln=True, align="C")
    
    return pdf.output(dest='S')

# --- 6. INTERFACE INTERATIVA (STREAMLIT) ---
st.title("🚜 Hub AgroTech - Gestão Integrada de Operações")

aba1, aba2, aba3 = st.tabs(["📝 Formulário de Campo", "📅 Escala Semanal", "📊 Dashboard BI"])

with aba1:
    st.subheader("📋 Nova Ordem de Serviço")
    with st.form("form_cadastro"):
        col1, col2 = st.columns([1, 1])
        with col1:
            dia_sel = st.selectbox("Dia do Planejamento", DIAS)
            equipe_sel = st.selectbox("Equipe Científica/Técnica", EQUIPES)
            periodo_sel = st.selectbox("Turno Alocado", PERIODOS)
            trator_sel = st.selectbox("Equipamento Motriz", TRATORES)
            implemento_sel = st.selectbox("Implemento Agrícola", IMPLEMENTOS)
        with col2:
            operador_sel = st.selectbox("Operador Técnico", OPERADORES)
            talhao_sel = st.selectbox("Localização / Alvo", TALHOES)
            atividade_txt = st.text_input("Atividade Detalhada", placeholder="Ex: Pulverização Fungicida")
            horimetro_num = st.number_input("Previsão de Horas", min_value=0.5, max_value=24.0, value=4.0, step=0.5)
            produto_txt = st.text_input("Insumo / Produto Utilizado", value="Nenhum")
            dosagem_num = st.number_input("Dosagem (L ou Kg/ha)", min_value=0.0, max_value=50.0, value=0.0, step=0.1)

        st.markdown("---")
        st.markdown("**Janela Climática de Segurança**")
        c_clima1, c_clima2 = st.columns(2)
        with c_clima1:
            temp_num = st.slider("Temperatura Máxima Recomendada (°C)", 15, 45, 30)
        with c_clima2:
            umi_num = st.slider("Umidade Mínima de Trabalho (%)", 20, 90, 55)

        btn_validar = st.form_submit_button("Validar e Gravar OS")

    if btn_validar:
        sucesso, mensagem = validar_regras_bd(dia_sel, equipe_sel, trator_sel, implemento_sel, operador_sel, periodo_sel)
        if not sucesso:
            st.error(mensagem)
        else:
            id_os = f"OS-{datetime.now().strftime('%d%H%M%S')}"
            dados_completos = {
                "id": id_os, "dia": dia_sel, "equipe": equipe_sel, "trator": trator_sel,
                "implemento": implemento_sel, "operador": operador_sel, "periodo": periodo_sel,
                "talhao": talhao_sel, "atividade": atividade_txt if atividade_txt.strip() else "Operação Geral",
                "produto": produto_txt, "dosagem": dosagem_num, "horimetro": horimetro_num,
                "temp": temp_num, "umi": umi_num
            }
            salvar_no_banco(dados_completos)
            st.success(f"Sucesso! {id_os} integrada ao sistema.")
            st.rerun()

with aba2:
    df_bd = carregar_dados_bd()
    if df_bd.empty:
        st.info("Aguardando os primeiros registros de campo para montar a matriz.")
    else:
        col_vazio, col_btn = st.columns([6, 1])
        with col_btn:
            if st.button("💥 Limpar Registros"):
                limpar_banco()
                st.rerun()
                
        st.subheader("📅 Quadro Geral de Alocações")
        df_bd['Resumo'] = df_bd.apply(lambda r: f"{r['trator']} + {r['implemento']} | {r['talhao']} ({r['periodo']})", axis=1)
        try:
            matriz = df_bd.pivot_table(index='equipe', columns='dia', values='Resumo', aggfunc=lambda x: ' / \n'.join(x)).fillna('-')
            cols_ordem = [d for d in DIAS if d in matriz.columns]
            st.dataframe(matriz[cols_ordem], use_container_width=True)
        except Exception:
            st.warning("Atualize os dados para recalcular o quadro.")

        st.markdown("---")
        st.subheader("📥 Emissão de Documentos de Campo")
        for idx, row in df_bd.iterrows():
            with st.expander(f"📌 {row['id']} - {row['equipe']} ({row['dia']})"):
                st.write(f"**Operação:** {row['atividade']} no **{row['talhao']}** com o operador **{row['operador']}**")
                try:
                    pdf_bytes = gerar_pdf_os(row)
                    st.download_button(
                        label=f"📥 Descarregar OS ({row['id']})",
                        data=pdf_bytes, file_name=f"{row['id']}.pdf",
                        mime="application/pdf", key=f"pdf_{row['id']}"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

with aba3:
    st.subheader("📊 Análise de Performance e Indicadores")
    df_bd = carregar_dados_bd()
    if df_bd.empty:
        st.info("Insira dados para visualizar os gráficos de BI.")
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total de Ordens Criadas", len(df_bd))
        with m2:
            st.metric("Horas de Trator Planejadas", f"{df_bd['horimetro_estimado'].sum()} h")
        with m3:
            st.metric("Setor Mais Ativo", df_bd['equipe'].mode()[0] if not df_bd['equipe'].empty else "N/A")
            
        st.markdown("---")
        g1, g2 = st.columns([1, 1])
        with g1:
            st.markdown("#### 🎯 Alocação de Horas por Trator")
            fig_trator = px.bar(df_bd, x='trator', y='horimetro_estimado', color='equipe',
                                labels={'trator':'Equipamento', 'horimetro_estimado':'Horas'}, barmode='stack')
            st.plotly_chart(fig_trator, use_container_width=True)
        with g2:
            st.markdown("#### 🚜 Participação de Uso por Equipe")
            fig_equipe = px.pie(df_bd, names='equipe', values='horimetro_estimado', hole=0.3)
            st.plotly_chart(fig_equipe, use_container_width=True)