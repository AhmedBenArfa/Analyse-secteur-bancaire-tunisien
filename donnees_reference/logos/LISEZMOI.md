<!-- Auteur : Ahmed Ben Arfa -->
# Logos des banques

Les logos sont la propriété de leurs banques respectives. Ils servent uniquement à identifier chaque
banque dans le rapport (segment par banque, colonne `icone` de `Dim_Banque`) ; ils ne sont pas couverts
par la licence du code du projet.

Chaque fichier `<code>.png` (code de la banque, comme dans `Dim_Banque`) est une vignette de
240 × 120 pixels, fond transparent, logo centré avec une marge de 10 pixels, téléchargée le
24/10/2026 (une requête à la fois, robots.txt respecté) puis rognée et réduite, sans autre
modification. Power Query la convertit en image intégrée (`data:image/png;base64,…`).

| Code | Banque | Source |
|---|---|---|
| AB | Amen Bank | fiche émetteur de la Bourse de Tunis : `https://www.tunis-stockexchange.com/sites/default/files/2025-07/LOGO%20Amen%20banque.PNG` (site de la banque : certificat incomplet) |
| ATB | Arab Tunisian Bank | `https://www.atb.tn/sites/default/files/atb-logo.png` (en-tête du site) |
| BH | BH Bank | `https://www.bhbank.tn/sites/default/files/logobh.svg` (en-tête du site, image vectorielle rendue en PNG) |
| BIAT | Banque Internationale Arabe de Tunisie | `https://www.biat.com.tn/sites/default/files/logobiat_0_0.png` |
| BNA | Banque Nationale Agricole | fiche émetteur de la Bourse de Tunis : `https://www.tunis-stockexchange.com/sites/default/files/2025-07/BNA.png` (site de la banque : sans réponse) |
| BT | Banque de Tunisie | `https://www.bt.com.tn/Themes/BT/Content/logo_bt.png` |
| BTE | Banque de Tunisie et des Emirats | `https://www.bte.com.tn/images/logo.png` |
| STB | Société Tunisienne de Banque | Wikimedia Commons : `https://upload.wikimedia.org/wikipedia/commons/0/06/Logo_STB.png` (site de la banque : certificat incomplet ; fichier de la fiche émetteur de la Bourse supprimé) |
| TJARI | Attijari Bank | `https://www.attijaribank.com.tn/sites/default/files/Logo_attijari_0.png` |
| UBCI | Union Bancaire pour le Commerce et l'Industrie | `https://www.ubci.tn/wp-content/themes/ubci/img/logo-banque-ubci.png` |
| UIB | Union Internationale de Banques | `https://www.uib.com.tn/logo/uib-logo.png` |
| WIB | Wifak International Bank | `https://www.wifakbank.com/build/assets/logo.0db6c6d8.webp` (converti en PNG) |

Solution de secours si un logo devait être retiré : pastilles rondes au code de la banque
(`python scripts/generer_theme.py`, aperçu `powerbi/theme/icones_banques.png`).
