# not-fan

Lista quem você segue e não te segue de volta, e quem te segue e você não segue de volta, usando o export de dados da sua própria conta no Instagram.

Não acessa o Instagram: a aplicação só lê o arquivo que você baixou.

## Como obter o export

No Instagram, peça o download das suas informações (Suas informações e permissões → Exportar suas informações). O formato HTML funciona. Você recebe um `.zip`, que pode usar direto ou extrair.

## No navegador

Abra o site, informe o link do perfil e escolha o `.zip` do export. A comparação acontece no seu navegador: o arquivo não é enviado para a Vercel.

O `vercel.json` publica só a pasta `public/`, sem passo de build. Um repositório só com o script Python não tem `index.html`, e a raiz do site responde 404.

## Na linha de comando

```bash
python3 not_fan.py https://www.instagram.com/seu_usuario/ ~/Downloads/instagram-seu_usuario-2026-11-16.zip
```

O segundo argumento aceita o `.zip` ou a pasta extraída. O link precisa ser do mesmo perfil dono do export; se não for, a aplicação para com erro.

## Testes

```bash
python3 -m unittest -v
```

## Privacidade

O export tem mensagens, fotos e outros dados pessoais. Não coloque esses arquivos neste repositório. O `.gitignore` já ignora `*.zip`, `instagram-*/` e `export*/`.
