import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday
import streamlit as st

# ==========================================
# 🔐 CONFIGURAÇÃO E ACESSO
# ==========================================
st.set_page_config(page_title="Dashboard Comercial - PAPAPÁ", layout="wide")

CODIGO_ACESSO = "Papapapa#@12"
token_hoje = f"access_comercial_{datetime.now().strftime('%Y%m%d')}"

if st.query_params.get("auth") != token_hoje:
    st.title("🔐 Acesso Restrito")
    codigo_digitado = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if codigo_digitado == CODIGO_ACESSO:
            st.query_params["auth"] = token_hoje
            st.rerun()
        else:
            st.error("Incorreto")
    st.stop()

# ==========================================
# 📊 DADOS
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
        st.error(f"Erro: {e}")
        return None, None

df_geral_hist, df_vendedores_hist = carregar_dados()

# --- DATAS E FERIADOS ---
class FeriadosBrasil(AbstractHolidayCalendar):
    rules = [Holiday('Ref', month=1, day=1), Holiday('Tira', month=4, day=21), Holiday('Maio', month=5, day=1)]

cal = FeriadosBrasil()
feriados = [d.date() for d in cal.holidays(start='2026-01-01', end='2026-12-31')]

with st.sidebar:
    data_selecionada = st.date_input("Data:", value=datetime(2026, 4, 16).date())

inicio_mes = data_selecionada.replace(day=1)
fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
dias_uteis = [d.date() for d in pd.date_range(inicio_mes, fim_mes, freq='B') if d.date() not in feriados]
data_limite = dias_uteis[-4] if len(dias_uteis) > 4 else dias_uteis[-1]
dias_totais_list = [d for d in dias_uteis if d <= data_limite]
dias_passados = len([d for d in dias_totais_list if d < data_selecionada])
dias_restantes = len([d for d in dias_totais_list if d >= data_selecionada])
percentual_esperado = (dias_passados / len(dias_totais_list)) * 100 if dias_totais_list else 100

def fmt_br(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt_m(v): return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# 📊 PERFORMANCE GERAL
# ==========================================
if df_geral_hist is not None:
    linha = df_geral_hist[df_geral_hist['Data'] == data_selecionada]
    if not linha.empty:
        r = linha.iloc[0]
        meta, fat, dig, dev = float(r['Meta_Mes']), float(r['Faturado_Acumulado']), float(r['Digitado_Acumulado']), abs(float(r['Devolucoes']))
        total_liq = (fat + dig) - dev
        perc = (total_liq / meta * 100) if meta > 0 else 0
        gap = perc - percentual_esperado
        falta = max(meta - total_liq, 0)
        ritmo = (falta / dias_restantes) if dias_restantes > 0 else 0

        st.subheader(f"📊 Resultado Geral (Ref: {data_selecionada.strftime('%d/%m')})")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("🎯 Meta", fmt_m(meta))
        c2.metric("✅ Faturado", fmt_m(fat))
        c3.metric("📝 Digitado", fmt_m(dig))
        c4.metric("🔄 Devoluções", f"-{fmt_m(dev)}")
        c5.metric("💰 Líquido", fmt_m(total_liq))
        c6.metric("🔥 Ating.", f"{perc:.1f}%", delta=f"{gap:.1f}%")
        c7.metric("📅 Ritmo", fmt_m(ritmo))

        st.info(f"**Análise de ciclo:** Devoluções: -{fmt_br(dev)} | Prazo: {data_limite.strftime('%d/%m')} | Ideal: {percentual_esperado:.1f}% ({fmt_br((percentual_esperado/100)*meta)})")

# ==========================================
# 👥 RANKING (A TABELA)
# ==========================================
st.markdown("---")
if df_vendedores_hist is not None:
    dv = df_vendedores_hist[df_vendedores_hist['Data'] == data_selecionada].copy()
    if not dv.empty:
        dv['total'] = (dv['Faturado_Acumulado'] + dv['Digitado_Acumulado']) - dv['Devolucoes'].abs()
        dv['ating'] = (dv['total'] / dv['Meta'] * 100).fillna(0)
        dv['tm'] = (dv['total'] / (dv['Fat_Ped'] + dv['Dig_Ped'])).replace([float('inf')], 0).fillna(0)
        dv['ritmo'] = ((dv['Meta'] - dv['total']).clip(lower=0) / dias_restantes).fillna(0)
        v_list = dv.sort_values(by="ating", ascending=False).to_dict('records')

        html = """<style>
            .tb { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; }
            .tb th { background: #f0f2f6; padding: 10px; border-bottom: 2px solid #ccc; }
            .tb td { padding: 10px; border-bottom: 1px solid #eee; text-align: center; }
            .bar-bg { background: #ddd; border-radius: 5px; width: 50px; height: 8px; display: inline-block; }
            .bar-fill { background: #29b5e8; height: 8px; border-radius: 5px; }
        </style><table class='tb'><thead><tr>
            <th>Pos.</th><th>Vendedor</th><th>Meta</th><th>Faturado</th><th>Digitado</th><th>Devoluções</th><th>Total Líq (TM)</th><th>Atingimento</th><th>Ritmo</th>
        </tr></thead><tbody>"""

        for i, v in enumerate(v_list):
            cor = "#2E7D32" if v['ating'] >= percentual_esperado else "#C62828"
            html += f"""<tr>
                <td>{i+1}º</td><td><b>{v['Vendedor']}</b></td><td>{fmt_br(v['Meta'])}</td>
                <td style='color:green'>{fmt_br(v['Faturado_Acumulado'])}</td>
                <td style='color:blue'>{fmt_br(v['Digitado_Acumulado'])}</td>
                <td style='color:red'>-{fmt_br(abs(v['Devolucoes']))}</td>
                <td><b>{fmt_br(v['total'])}</b><br><small>TM: {fmt_br(v['tm'])}</small></td>
                <td><div class='bar-bg'><div class='bar-fill' style='width:{min(v['ating'],100)}%'></div></div><br><b style='color:{cor}'>{v['ating']:.1f}%</b></td>
                <td style='color:#E64A19'><b>{fmt_br(v['ritmo'])}</b></td>
            </tr>"""
        
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        st.success(f"🚀 **Destaque do Mês:** Atualmente **{v_list[0]['Vendedor']}** lidera com **{v_list[0]['ating']:.1f}%**!")

st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none !important; }</style>", unsafe_allow_html=True)
