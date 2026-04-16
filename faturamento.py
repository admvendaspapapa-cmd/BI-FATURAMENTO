import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday
import streamlit.components.v1 as components

# ==========================================
# 🔐 PROTEÇÃO DE ACESSO
# ==========================================

st.set_page_config(
    page_title="Dashboard Comercial - PAPAPÁ",
    layout="wide",
    initial_sidebar_state="expanded"
)

CODIGO_ACESSO = "Papapapa#@12"
# Token muda diariamente para segurança básica
token_hoje = f"access_comercial_{datetime.now().strftime('%Y%m%d')}"

query_params = st.query_params
acesso_valido = query_params.get("auth") == token_hoje

if not acesso_valido:
    st.title("🔐 Acesso Restrito - Comercial Papapá")
    try:
        st.image("Papapa-azul.png", width=200)
    except:
        st.write("### 💙 Papapá")

    codigo_digitado = st.text_input("Digite a senha de acesso", type="password")
    if st.button("Entrar"):
        if codigo_digitado == CODIGO_ACESSO:
            st.query_params["auth"] = token_hoje
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# ==========================================
# 📊 CONFIGURAÇÃO E CARREGAMENTO
# ==========================================

@st.cache_data(ttl=60)
def carregar_dados():
    try:
        arquivo = "dados_performance 1.xlsx"
        # Carrega as abas garantindo que existam
        df_g = pd.read_excel(arquivo, sheet_name="Geral")
        df_v = pd.read_excel(arquivo, sheet_name="Vendedores")

        # Normalização de datas para tipo date (comparável com st.date_input)
        df_g['Data'] = pd.to_datetime(df_g['Data']).dt.date
        df_v['Data'] = pd.to_datetime(df_v['Data']).dt.date
        
        # Garante que valores nulos sejam 0 para não quebrar cálculos
        df_g = df_g.fillna(0)
        df_v = df_v.fillna(0)
        
        return df_g, df_v
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return None, None

df_geral_hist, df_vendedores_hist = carregar_dados()

# --- CONFIGURAÇÃO DE FERIADOS ---
class FeriadosBrasil(AbstractHolidayCalendar):
    rules = [
        Holiday('Confraternização Universal', month=1, day=1),
        Holiday('Tiradentes', month=4, day=21),
        Holiday('Dia do Trabalho', month=5, day=1),
        Holiday('Independência', month=9, day=7),
        Holiday('Nossa Sra Aparecida', month=10, day=12),
        Holiday('Finados', month=11, day=2),
        Holiday('Proclamação da República', month=11, day=15),
        Holiday('Natal', month=12, day=25),
    ]

cal = FeriadosBrasil()
# Ajustado para cobrir o ano atual dinamicamente
ano_atual = datetime.now().year
feriados_pandas = cal.holidays(start=f'{ano_atual}-01-01', end=f'{ano_atual}-12-31')
lista_feriados = [d.date() for d in feriados_pandas]

# --- SIDEBAR E FILTRO ---
with st.sidebar:
    try:
        st.image("Papapa-azul.png", width=180)
    except:
        st.subheader("💙 Papapá")

    st.markdown("---")
    st.header("⚙️ Filtro")
    # Valor padrão é ontem (D-1), pois faturamento costuma ser consolidado no dia anterior
    data_selecionada = st.date_input("Data de referência:", value=datetime.now().date() - timedelta(days=1), format="DD/MM/YYYY")

    if st.sidebar.button("Sair (Limpar Sessão)"):
        st.query_params.clear()
        st.rerun()

# ==========================================
# 📝 LÓGICA DE DATAS (D-1 ÚTIL)
# ==========================================
inicio_mes = data_selecionada.replace(day=1)
# Encontra o último dia do mês
proximo_mes = inicio_mes + timedelta(days=32)
fim_mes_civil = proximo_mes.replace(day=1) - timedelta(days=1)

# Lista de dias úteis reais (Seg-Sex e sem feriado)
dias_uteis_reais = pd.date_range(inicio_mes, fim_mes_civil, freq='B')
dias_uteis_reais = [d.date() for d in dias_uteis_reais if d.date() not in lista_feriados]

# Regra Papapá: Faturamento costuma encerrar 4 dias úteis antes do fim do mês? (Mantido lógica original)
data_limite_faturamento = dias_uteis_reais[-4] if len(dias_uteis_reais) > 4 else dias_uteis_reais[-1]
dias_uteis_totais_list = [d for d in dias_uteis_reais if d <= data_limite_faturamento]
dias_uteis_comerciais_totais = len(dias_uteis_totais_list)

dias_uteis_passados = len([d for d in dias_uteis_totais_list if d < data_selecionada])
percentual_esperado = (dias_uteis_passados / dias_uteis_comerciais_totais) * 100 if dias_uteis_comerciais_totais > 0 else 100

# ==========================================
# 📊 RESULTADO GERAL (EMPRESA TODA)
# ==========================================
st.subheader(f"📊 Resultado Consolidado - Papapá (Ref: {data_selecionada.strftime('%d/%m')})")

def fmt_m(v): 
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

if df_geral_hist is not None:
    linha = df_geral_hist[df_geral_hist['Data'] == data_selecionada]
    
    if not linha.empty:
        meta_val = float(linha.iloc[0]['Meta_Mes'])
        fat_val = float(linha.iloc[0]['Faturado_Acumulado'])
        dig_val = float(linha.iloc[0]['Digitado_Acumulado'])
        dev_val = float(linha.iloc[0].get('Devolucao_Acumulada', 0))

        total_liq = (fat_val + dig_val) - abs(dev_val)
        ating_perc = (total_liq / meta_val) * 100 if meta_val > 0 else 0
        gap_linear = ating_perc - percentual_esperado
        falta_r = max(meta_val - total_liq, 0)

        if gap_linear < -2 and falta_r > 0:
            st.error(f"⚠️ **Ritmo Atrasado:** {abs(gap_linear):.1f}% abaixo do ideal para o dia útil {dias_uteis_passados}.")
        elif falta_r <= 0:
            st.balloons()
            st.success("🏆 **META BATIDA!**")

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("🎯 Meta", fmt_m(meta_val))
        c2.metric("✅ Faturado", fmt_m(fat_val))
        c3.metric("📝 Digitado", fmt_m(dig_val))
        c4.metric("🔄 Devoluções", f"-{fmt_m(abs(dev_val))}")
        c5.metric("💰 Total Líquido", fmt_m(total_liq))
        c6.metric("🚩 Falta (Gap)", fmt_m(falta_r))
        c7.metric("🔥 Atingimento", f"{ating_perc:.1f}%", delta=f"{gap_linear:.1f}% vs Ideal")
    else:
        st.warning(f"Sem dados consolidados para a data {data_selecionada.strftime('%d/%m/%Y')}.")

# ==========================================
# 📈 PERFORMANCE POR TIME (ABA VENDEDORES)
# ==========================================
st.markdown("---")
st.subheader("👥 Performance por Time Comercial")

if df_vendedores_hist is not None:
    dados_v = df_vendedores_hist[df_vendedores_hist['Data'] == data_selecionada].copy()

    if not dados_v.empty:
        dados_v['Total_Liq'] = (dados_v['Faturado'] + dados_v['Digitado']) - dados_v['Devolucoes'].abs()
        dados_v['Ating'] = (dados_v['Total_Liq'] / dados_v['Meta'] * 100).fillna(0)

        html_table = """
        <style>
            .tab-papapa { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
            .tab-papapa th { background-color: #f0f2f6; padding: 12px; text-align: left; color: #31333F; border-bottom: 2px solid #ccc; }
            .tab-papapa td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
            .col-bold { font-weight: bold; color: #1f1f1f; }
            .text-red { color: #C62828; font-weight: bold; }
            .text-green { color: #2E7D32; font-weight: bold; }
        </style>
        <table class='tab-papapa'>
        <thead>
            <tr>
                <th>Time / Vendedor</th>
                <th>Meta</th>
                <th>Faturado</th>
                <th>Digitado</th>
                <th>Devoluções</th>
                <th>Total Líquido</th>
                <th>Atingimento (%)</th>
            </tr>
        </thead>
        <tbody>
        """

        for _, r in dados_v.iterrows():
            cor_status = "text-green" if r['Ating'] >= percentual_esperado else "text-red"
            html_table += f"""
            <tr>
                <td class='col-bold'>{r['Vendedor']}</td>
                <td>{fmt_m(r['Meta'])}</td>
                <td>{fmt_m(r['Faturado'])}</td>
                <td>{fmt_m(r['Digitado'])}</td>
                <td style='color: #C62828;'>-{fmt_m(abs(r['Devolucoes']))}</td>
                <td><b>{fmt_m(r['Total_Liq'])}</b></td>
                <td class='{cor_status}'>{r['Ating']:.1f}%</td>
            </tr>
            """
        
        html_table += "</tbody></table>"
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.info("Selecione uma data com registros para ver o detalhamento por vendedor.")

# Remove setas de delta padrão do Streamlit para um visual mais limpo
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none !important; }</style>", unsafe_allow_html=True)
