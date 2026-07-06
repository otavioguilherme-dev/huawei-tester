import requests
import json

# Configurações do iMaster NCE
IMASTER_IP = "https://159.138.213.219:18008" # Altere para o IP do seu iMaster
USERNAME = "api-otavio"
PASSWORD = "Ot@vio2912"

def obter_token():
    """1. Autentica na API do iMaster e obtém o Token de Acesso"""
    url = f"https://{IMASTER_IP}:18002/v1/auth/tokens" # Porta padrão API norte
    headers = {"Content-Type": "application/json"}
    payload = {"userName": USERNAME, "password": PASSWORD}
    
    # Desabilitar avisos de SSL em laboratório se usar certificado self-signed
    requests.packages.urllib3.disable_warnings() 
    
    response = requests.post(url, json=payload, headers=headers, verify=False)
    if response.status_code == 201 or response.status_code == 200:
        return response.json()['data']['token_id']
    else:
        raise Exception(f"Falha na autenticação: {response.text}")

def analisar_localidade(nome_localidade, token):
    """2. Pesquisa os problemas da localidade informada"""
    headers = {
        "X-AUTH-TOKEN": token,
        "Content-Type": "application/json"
    }
    
    print(f"\n🔍 Analisando localidade: {nome_localidade}...")
    
    # Passo A: Buscar o ID do Site/Localidade pelo nome
    url_site = f"https://{IMASTER_IP}:18002/controller/campus/v1/sdwan/net/sites?name={nome_localidade}"
    res_site = requests.get(url_site, headers=headers, verify=False)
    
    if not res_site.json().get('data'):
        print("❌ Localidade não encontrada no iMaster.")
        return
        
    site_id = res_site.json()['data'][0]['id']
    
    # Passo B: Buscar alarmes ativos para os dispositivos desse Site
    url_alarmes = f"https://{IMASTER_IP}:18002/controller/campus/v1/alarms?siteId={site_id}&status=active"
    res_alarmes = requests.get(url_alarmes, headers=headers, verify=False)
    alarmes = res_alarmes.json().get('data', [])
    
    # Passo C: Analisar os resultados coletados
    print("\n--- RESULTADO DA ANÁLISE ---")
    if len(alarmes) == 0:
        print("✅ Links e Conectividade: Tudo Operacional. Nenhum alarme ativo.")
    else:
        print(f"❌ PROBLEMA ENCONTRADO! Existem {len(alarmes)} alarmes ativos nesta localidade:")
        for alarme in alarmes:
            print(f"   - [Gravidade: {alarme['severity']}] -> {alarme['alarmName']} (Afeta: {alarme['objectName']})")
            
            # Validação simples de Link Caído ou Perda
            if "link" in alarme['alarmName'].lower() or "down" in alarme['alarmName'].lower():
                print("     💡 Alerta de Queda de Link ou Interface Desconectada.")
            if "loss" in alarme['alarmName'].lower() or "drop" in alarme['alarmName'].lower():
                print("     💡 Alerta de Perda de Pacotes detectado no circuito.")

# Execução do script de teste
if __name__ == "__main__":
    try:
        token = obter_token()
        # Subescreva com o nome exato de um site/filial cadastrado no seu iMaster
        analisar_localidade(nome_localidade="Filial_SaoPaulo", token=token)
    except Exception as e:
        print(f"Erro: {e}")
