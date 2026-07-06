import streamlit as st
import requests

# --- 1. VALIDAÇÃO DOS SECRETS ---
try:
    IMASTER_IP = st.secrets["IMASTER_IP"]
    USERNAME = st.secrets["USERNAME"]
    PASSWORD = st.secrets["PASSWORD"]
    config_ok = True
except Exception:
    config_ok = False

# --- FUNÇÃO AUXILIAR CORRIGIDA ---
def limpar_ip(ip):
    """Remove protocolos e barras caso tenham sido digitados por engano"""
    if not ip:
        return ""
    return ip.replace("https://", "").replace("http://", "").strip("/")

# --- 2. FUNÇÕES DE API ---
def obter_token():
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Tentaremos as duas portas e caminhos conhecidos na sua versão
    combinacoes = [
        {"url": f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens", "tipo": "wan_padrao"},
        {"url": f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens", "tipo": "wan_estrito"},
        {"url": f"https://{ip_limpo}:18002/v1/auth/tokens", "tipo": "campus"}
    ]
    
    requests.packages.urllib3.disable_warnings() 
    
    for item in combinacoes:
        url = item["url"]
        
        # Formata o JSON de acordo com o padrão do módulo correspondente
        if item["tipo"] == "wan_estrito":
            payload = {
                "authParams": {
                    "userName": USERNAME,
                    "password": PASSWORD
                }
            }
        else:
            payload = {
                "userName": USERNAME,
                "password": PASSWORD
            }
            
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                verify=False, 
                timeout=5
            )
            
            # Se autenticar, captura o token
            if response.status_code in [200, 201]:
                dados_resposta = response.json()
                # O token pode vir em estruturas diferentes dependendo do endpoint
                if 'data' in dados_resposta and 'token_id' in dados_resposta['data']:
                    return dados_resposta['data']['token_id']
                elif 'token' in dados_resposta:
                    return dados_resposta['token']
                elif 'access_token' in dados_resposta:
                    return dados_resposta['access_token']
        except Exception:
            continue
            
    return None

@st.cache_data(ttl=300) # Guarda a lista por 5 minutos para performance
def listar_todos_os_sites(token):
    """Busca todas as localidades ativas no iMaster para gerar a lista"""
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Testa as duas portas principais para o inventário
    portas = ["18008", "18002"]
    for porta in portas:
        url = f"https://{ip_limpo}:{porta}/controller/campus/v1/sdwan/net/sites"
        headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                dados = response.json().get('data', [])
                # Mapeia Nome do Site -> ID do Site
                return {site['name']: site['id'] for site in dados if 'name' in site}
        except Exception:
            continue
    return {}

def buscar_alarmes_por_id(site_id, token):
    """Interroga os alarmes ativos diretamente pelo ID mapeado"""
    ip_limpo = limpar_ip(IMASTER_IP)
    portas = ["18008", "18002"]
    
    for porta in portas:
        url_alarmes = f"https://{ip_limpo}:{porta}/controller/campus/v1/alarms?siteId={site_id}&status=active"
        headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
        try:
            res_alarmes = requests.get(url_alarmes, headers=headers, verify=False, timeout=5)
            if res_alarmes.status_code == 200:
                alarmes = res_alarmes.json().get('data', [])
                return alarmes, None
        except Exception as e:
            last_error = e
            continue
    return None, f"Erro ao consultar dados de alarmes nas portas testadas: {last_error}"

# --- 3. INTERFACE GRÁFICA ---
st.set_page_config(page_title="Troubleshooting iMaster", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting - iMaster NCE")

if not config_ok:
    st.error("⚠️ Configuração Incompleta! Você precisa adicionar IMASTER_IP, USERNAME e PASSWORD nos 'Secrets' do Streamlit.")
else:
    # 1. Tenta autenticar e gerar a lista de pontos no início do carregamento da página
    with st.spinner("Autenticando e sincronizando lista de pontos ativos..."):
        token_atual = obter_token()
        if token_atual:
            dicionario_sites = listar_todos_os_sites(token_atual)
        else:
            dicionario_sites = {}
            st.error("❌ Falha na autenticação do iMaster. Verifique suas credenciais de API nos Secrets.")

    # 2. Se encontrou sites, renderiza o selectbox inteligente
    if dicionario_sites:
        st.write("Selecione um ponto abaixo no menu para iniciar a análise automatizada de quedas e perdas.")
        
        lista_nomes = sorted(list(dicionario_sites.keys()))
        site_selecionado = st.selectbox("Selecione a Localidade para Consulta:", lista_nomes)
        
        if st.button("Analisar Saúde do Ponto"):
            id_do_site = dicionario_sites[site_selecionado]
            
            with st.spinner(f"Interrogando alarmes de {site_selecionado}..."):
                alarmes, erro = buscar_alarmes_por_id(id_do_site, token_atual)
                
                if erro:
                    st.error(erro)
                elif len(alarmes) == 0:
                    st.success(f"✅ **STATUS: SAUDÁVEL**. O ponto **{site_selecionado}** está operando normalmente sem alarmes.")
                else:
                    st.error(f"❌ **STATUS: COM PROBLEMA ({len(alarmes)} alarme(s) ativo(s))**")
                    
                    # Formata os alarmes de maneira limpa para o operador ler
                    dados_tabela = []
                    for al_item in alarmes:
                        dados_tabela.append({
                            "Gravidade": al_item.get('severity'),
                            "Alarme": al_item.get('alarmName'),
                            "Componente": al_item.get('objectName'),
                            "Início do Evento": al_item.get('startTime')
                        })
                    st.dataframe(dados_tabela, use_container_width=True)
    else:
        if token_atual:
            st.warning("⚠️ Conectado ao iMaster, porém nenhuma localidade/site foi encontrado no inventário da API de Campus.")
