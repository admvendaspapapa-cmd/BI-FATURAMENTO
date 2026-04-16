import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday
import streamlit as st

# ==========================================
# 🔐 PROTEÇÃO DE ACESSO
# ==========================================
st.set_page_config(page_title="Dashboard Comercial - PAPAPÁ", layout="wide", initial_sidebar_state="expanded")

CODIGO_ACESSO = "Papapapa#@12"
token_hoje = f"access_comercial_{datetime.now().strftime('%Y%m%d')}"

if st.query_params.get("auth") != token_hoje:
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
        df_g = pd.read_excel(arquivo, sheet_name="Geral")
        df_v = pd.read_excel(arquivo, sheet_name="Vendedores")
        df_g['Data'] = pd.to_datetime(df_g['Data']).dt.date
        df_v['Data'] = pd.to_datetime(df_v['Data']).dt.date
        return df_g, df_v
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo Excel: {e}")
        return None, None

df_geral_hist, df_vendedores_hist = carregar_dados()

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
feriados_pandas = cal.holidays(start='2026-01-01', end='2026-12-31')
lista_feriados = [d.date() for d in feriados_pandas]

with st.sidebar:
    try:
        st.image("Papapa-azul.png", width=180)
    except:
        st.subheader("💙 Papapá")
    st.markdown("---")
    st.header("⚙️ Filtro")
    data_selecionada = st.date_input("Data de referência:", value=datetime(2026, 4, 16).date(), format="DD/MM/YYYY")
    if st.button("Sair"):
        st.query_params.clear()
        st.rerun()

# ==========================================
# 📝 LÓGICA DE DATAS
# ==========================================
inicio_mes = data_selecionada.replace(day=1)
fim_mes_civil = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
dias_uteis_reais = [d.date() for d in pd.date_range(inicio_mes, fim_mes_civil, freq='B') if d.date() not in lista_feriados]

data_limite_faturamento = dias_uteis_reais[-4] if len(dias_uteis_reais) > 4 else dias_uteis_reais[-1]
dias_uteis_totais_list = [d for d in dias_uteis_reais if d <= data_limite_faturamento]
dias_uteis_comerciais_totais = len(dias_uteis_totais_list)

dias_uteis_anteriores = [d for d in dias_uteis_totais_list if d < data_selecionada]
dias_uteis_passados = len(dias_uteis_anteriores)
data_ref_calculo = dias_uteis_anteriores[-1] if dias_uteis_passados > 0 else inicio_mes

dias_uteis_restantes = len([d for d in dias_uteis_totais_list if d >= data_selecionada])
percentual_esperado = (dias_uteis_passados / dias_uteis_comerciais_totais) * 100 if dias_uteis_comerciais_totais > 0 else 100

def fmt_m(v): return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt_br(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# 📝 BLOCO 1: PERFORMANCE GERAL
# ==========================================
if df_geral_hist is not None:
    linha_g = df_geral_hist[df_geral_hist['Data'] == data_selecionada]
    if not linha_g.empty:
        rg = linha_g.iloc[0]
        meta_g, fat_g, dig_g, dev_g = float(rg['Meta_Mes']), float(rg['Faturado_Acumulado']), float(rg['Digitado_Acumulado']), abs(float(rg['Devolucoes']))
        total_liq_g = (fat_g + dig_g) - dev_g
        perc_g = (total_liq_g / meta_g * 100) if meta_g > 0 else 0
        gap_g = perc_g - percentual_esperado
        falta_g = max(meta_g - total_liq_g, 0)
        ritmo_g = (falta_g / dias_uteis_restantes) if dias_uteis_restantes > 0 else 0

        st.subheader(f"📊 Resultado Consolidado - Papapá (Ref: {data_ref_calculo.strftime('%d/%m')})")
        
        c1, c2, c3, c_dev, c_total, c4, c5 = st.columns(7)
        c1.metric("🎯 Meta", fmt_m(meta_g))
        c2.metric("✅ Faturado", fmt_m(fat_g))
        c3.metric("📝 Digitado", fmt_m(dig_g))
        c_dev.metric("🔄 Devoluções", f"-{fmt_m(dev_g)}")
        c_total.metric("💰 Total Líquido", fmt_m(total_liq_g))
        c4.metric("🚩 Gap Real", fmt_m(falta_g))
        c5.metric("🔥 Atingimento", f"{perc_g:.1f}%", delta=f"{gap_g:.1f}% vs Ideal")

        st.markdown(f"""> **Análise de ciclo:**
> * Devoluções acumuladas: **-{fmt_br(dev_g)}**.
> * Prazo final de faturamento: **{data_limite_faturamento.strftime('%d/%m')}**.
> * Dias úteis restantes (contando com a data selecionada): **{dias_uteis_restantes}**.
> * O atingimento ideal para hoje é de **{percentual_esperado:.1f}%** (equivale a **{fmt_br((percentual_esperado/100)*meta_g)}**).""")

# ==========================================
# 📈 PERFORMANCE POR VENDEDOR (RANKING)
# ==========================================
st.markdown("---")
st.subheader(f"👥 Ranking Individual - {data_selecionada.strftime('%B').capitalize()}")

if df_vendedores_hist is not None:
    # Filtra os dados pela data selecionada
    dados_v = df_vendedores_hist[df_vendedores_hist['Data'] == data_selecionada].copy()
    
    if not dados_v.empty:
        # 1. Cálculos de Performance
        dados_v['total_row'] = (dados_v['Faturado_Acumulado'] + dados_v['Digitado_Acumulado']) - dados_v['Devolucoes'].abs()
        dados_v['ating_row'] = (dados_v['total_row'] / dados_v['Meta'] * 100).fillna(0)
        dados_v['val_id_row'] = (percentual_esperado / 100) * dados_v['Meta']
        
        # 2. Cálculo do Ticket Médio (TM) - Protegido contra erro de divisão por zero
        soma_pedidos = dados_v['Fat_Ped'] + dados_v['Dig_Ped']
        dados_v['tm_row'] = (dados_v['total_row'] / soma_pedidos).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        # 3. Ritmo Diário Necessário
        dados_v['ritmo_row'] = ((dados_v['Meta'] - dados_v['total_row']).clip(lower=0) / dias_uteis_restantes).fillna(0)
        
        # Ordena pelo maior atingimento
        v_lista = dados_v.sort_values(by="ating_row", ascending=False).to_dict('records')
        
        # 4. CONSTRUÇÃO DA TABELA HTML
        html_ranking = """
        <style>
            .tab-performance { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; color: #31333F; }
            .tab-performance th { background-color: #f0f2f6; padding: 10px; text-align: center; border-bottom: 2px solid #ccc; }
            .tab-performance td { padding: 10px; text-align: center; border-bottom: 1px solid #eee; }
            .prog-bg { background-color: #ddd; border-radius: 10px; width: 50px; height: 8px; display: inline-block; }
            .prog-bar { background-color: #29b5e8; height: 8px; border-radius: 10px; }
            .col-vendedor { text-align: left !important; font-weight: bold; width: 180px; }
            .sub-tm { font-size: 11px; color: #757575; display: block; margin-top: 2px; }
        </style>
        <table class='tab-performance'>
            <thead>
                <tr>
                    <th>Pos.</th>
                    <th class='col-vendedor'>Vendedor</th>
                    <th>Meta</th>
                    <th>Faturado</th>
                    <th>Digitado</th>
                    <th>Devoluções</th>
                    <th>Total Líq (TM)</th>
                    <th>Atingimento</th>
                    <th>Ideal Hoje</th>
                    <th>Ritmo</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, v in enumerate(v_lista):
            cor_ating = "#2E7D32" if v["ating_row"] >= percentual_esperado else "#C62828"
            largura_barra = min(v["ating_row"], 100)

            html_ranking += f"""
                <tr>
                    <td>{i+1}º</td>
                    <td class='col-vendedor'>{v['Vendedor']}</td>
                    <td>{fmt_br(v['Meta'])}</td>
                    <td style='color:#2E7D32'>{fmt_br(v['Faturado_Acumulado'])}</td>
                    <td style='color:#1565C0'>{fmt_br(v['Digitado_Acumulado'])}</td>
                    <td style='color:#C62828'>-{fmt_br(abs(v['Devolucoes']))}</td>
                    <td><b>{fmt_br(v['total_row'])}</b><span class='sub-tm'>TM: {fmt_br(v['tm_row'])}</span></td>
                    <td>
                        <div class='prog-bg'><div class='prog-bar' style='width:{largura_barra}%'></div></div><br>
                        <span style='color:{cor_ating}; font-weight:bold;'>{v['ating_row']:.1f}%</span>
                    </td>
                    <td>{fmt_br(v['val_id_row'])}</td>
                    <td style='color:#E64A19; font-weight:bold;'>{fmt_br(v['ritmo_row'])}</td>
                </tr>
            """

        html_ranking += "</tbody></table>"
        
        # Renderiza a tabela
        st.markdown(html_ranking, unsafe_allow_html=True)
        
        # Mensagem de destaque
        st.success(f"🚀 **Destaque:** **{v_lista[0]['Vendedor']}** lidera o ranking com **{v_lista[0]['ating_row']:.1f}%**! 🔥")
    else:
        st.warning("⚠️ Nados dados encontrados para esta data.")
