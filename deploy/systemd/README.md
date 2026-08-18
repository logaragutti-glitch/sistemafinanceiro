# Execução contínua em VPS ou Raspberry Pi

O arquivo `sistema-financeiro.service` mantém `main.py` rodando, reinicia o processo se houver uma falha e deixa os horários dos sete cenários centralizados no próprio projeto.

## Instalação

Na máquina de produção, clone o repositório no diretório padrão do usuário `ubuntu`, instale as dependências e copie os arquivos secretos sem colocá-los no Git:

```bash
git clone https://github.com/logaragutti-glitch/sistemafinanceiro.git ~/sistema-financeiro
cd ~/sistema-financeiro
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# coloque credentials.json na raiz e preencha .env
```

O serviço fornecido usa `/usr/bin/python3` por padrão. Em uma instalação com ambiente virtual, ajuste `ExecStart` para:

```ini
ExecStart=%h/sistema-financeiro/.venv/bin/python -u main.py
```

Depois instale e ative o serviço:

```bash
sudo cp deploy/systemd/sistema-financeiro.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro
sudo systemctl status sistema-financeiro
```

## Diagnóstico e manutenção

Antes de ativar o serviço, execute a verificação local e, depois de confirmar o acesso à planilha, a verificação online:

```bash
python3 -m scripts.verificar_producao
python3 -m scripts.verificar_producao --online
```

Para rodar um cenário manualmente sem esperar o horário agendado:

```bash
python3 -m scripts.run_once --cenario 1
```

Para acompanhar o serviço:

```bash
journalctl -u sistema-financeiro -f
```

Os extratos continuam sendo baixados manualmente antes das 06:00 e devem ser salvos em `extratos/` com o nome exato de cada conta. O agendador não deve ser iniciado em duas máquinas ao mesmo tempo, pois isso poderia processar o mesmo período em paralelo.
