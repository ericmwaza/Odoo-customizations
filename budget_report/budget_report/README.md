# Budget Report Module for Odoo 18

## Description
Ce module génère des rapports d'exécution budgétaire avec exports PDF (paysage) et Excel. Il permet de suivre les encaissements, exécutions et calcule automatiquement les soldes et taux de réalisation.

## Fonctionnalités

### 1. Configuration
- **Paramètres → Comptabilité → Rapport Budget**
  - Définir les comptes analytiques d'encaissement (recettes)
  - Définir les comptes analytiques d'exécution (dépenses)

### 2. Génération de Rapport
- **Comptabilité → Rapports → Rapport Budget**
- Sélectionner:
  - Budget (poste budgétaire)
  - Période (date début/fin)
  - Type: PDF paysage ou Excel

### 3. Colonnes du Rapport
1. **Rubriques budgétaires** - Nom du compte analytique
2. **Crédit annuel accordé** - Montant budgété
3. **Encaissement** - Somme des lignes analytiques des comptes d'encaissement
4. **Exécution** - Somme des lignes analytiques des comptes d'exécution
5. **Solde Théorique annuel à engager** = Crédit annuel - Encaissement
6. **Solde Réel** = Encaissement - Exécution
7. **Taux de réalisation** = (Exécution ÷ Crédit annuel) × 100%

## Installation

1. **Copier le module dans addons:**
```bash
sudo cp -r /home/eric/Documents/budget_report /opt/odoo/addons/
```

2. **Redémarrer Odoo:**
```bash
sudo systemctl restart odoo
```

3. **Installer le module:**
   - Aller dans Apps
   - Retirer le filtre "Apps"
   - Chercher "Budget Report"
   - Cliquer sur "Installer"

## Configuration Requise

### Dépendances
- `account` - Comptabilité
- `account_budget` - Gestion budgétaire
- `analytic` - Comptabilité analytique

### Configuration Initiale
1. Aller dans **Paramètres → Comptabilité**
2. Descendre à la section **Rapport Budget**
3. Sélectionner les comptes analytiques pour:
   - Encaissement (ex: Compte de ventes, revenus)
   - Exécution (ex: Comptes de dépenses, achats)

## Utilisation

### Générer un Rapport PDF
1. Aller dans **Comptabilité → Rapports → Rapport Budget**
2. Sélectionner le budget
3. Choisir la période
4. Sélectionner "PDF (Paysage)"
5. Cliquer sur "Générer"

### Générer un Rapport Excel
1. Aller dans **Comptabilité → Rapports → Rapport Budget**
2. Sélectionner le budget
3. Choisir la période
4. Sélectionner "Excel"
5. Cliquer sur "Générer"
6. Le fichier sera téléchargé automatiquement

## Structure du Module

```
budget_report/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── budget_report_config.py      # Configuration des comptes analytiques
│   └── budget_report_wizard.py      # Assistant de génération
├── views/
│   ├── budget_report_config_views.xml    # Vue configuration
│   ├── budget_report_wizard_views.xml    # Vue assistant
│   └── budget_report_menus.xml           # Menus
├── reports/
│   ├── __init__.py
│   ├── budget_report_pdf.xml        # Template PDF QWeb
│   ├── budget_report_excel.py       # Générateur Excel
│   └── budget_reports.xml           # Définition rapport
└── security/
    └── ir.model.access.csv          # Droits d'accès
```

## Notes Techniques

### Calculs
- Les montants d'encaissement sont calculés en sommant les lignes analytiques dont le compte appartient aux comptes d'encaissement configurés
- Les montants d'exécution sont calculés en sommant (en valeur absolue) les lignes analytiques dont le compte appartient aux comptes d'exécution configurés
- Tous les calculs sont effectués pour la période sélectionnée

### Format PDF
- Orientation: Paysage (A4)
- Toutes les valeurs monétaires formatées avec 2 décimales
- Pourcentages affichés avec symbole %
- Ligne de total en bas du tableau

### Format Excel
- Même structure que le PDF
- Formatage professionnel avec couleurs
- Formules pour totaux
- Légende incluse

## Support
Pour toute question ou problème, contacter: ericmwaza@gmail.com

## Licence
LGPL-3

## Version
18.0.1.0.0
