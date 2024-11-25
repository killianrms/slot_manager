# Slot Manager

Bienvenue sur le dépôt GitHub de **Slot Manager**, une solution innovante pour automatiser la gestion des salons Discord. Cet outil permet aux administrateurs de serveurs Discord de créer des "slots" personnalisés où les utilisateurs peuvent temporairement obtenir des permissions spéciales, avec une gestion entièrement automatisée.

## Description

Slot Manager est conçu pour :

- **Créer des salons dédiés pour les utilisateurs** : Donnez à un utilisateur la possibilité d'écrire et de faire des annonces dans un salon nominatif.
- **Durée limitée** : Gérez automatiquement la durée pendant laquelle un utilisateur peut accéder à son salon.
- **Gestion des permissions** : Contrôlez le nombre de pings ou mentions que chaque utilisateur peut envoyer par jour.
- **Blocage automatisé** : Verrouillez le salon une fois le temps imparti expiré.

Cet outil fait gagner un temps précieux aux administrateurs en automatisant des processus de gestion fastidieux.

## Fonctionnalités principales

- **Attribution automatique des permissions** : Les utilisateurs peuvent temporairement obtenir des droits étendus dans un salon.
- **Configuration personnalisée** : Définissez les durées, limites de pings et autres paramètres.
- **Gestion centralisée** : Une interface unique pour surveiller et administrer les salons créés.
- **Notifications** : Envoi d'alertes pour informer l'utilisateur de l'état de son salon (temps restant, expiration, etc.).

## Technologies utilisées

- **Langage principal** : Python
- **Librairie Discord** : `discord.py` pour interagir avec l'API Discord
- **Base de données** : PostgreSQL pour suivre les salons et utilisateurs
- **Outils supplémentaires** :
  - `dotenv` pour la gestion des configurations
  - `asyncio` pour les tâches asynchrones

## Installation

Pour installer et utiliser Slot Manager :

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/killianrms/slot_manager.git
   ```
2. Accédez au dossier du projet :
   ```bash
   cd slot_manager
   ```
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Configurez les variables d'environnement dans un fichier `.env` :
   ```env
   DISCORD_TOKEN=VotreJetonDiscord
   DATABASE_URL=sqlite:///slot_manager.db
   ```
5. Lancez le bot :
   ```bash
   python bot.py
   ```

## Contribution

Nous accueillons avec plaisir les contributions pour améliorer Slot Manager.

1. **Forkez ce dépôt**
2. **Créez une branche** :
   ```bash
   git checkout -b feature/ma-nouvelle-fonctionnalite
   ```
3. **Apportez vos modifications et validez-les**
4. **Soumettez une pull request**

Merci de consulter notre guide de contribution pour des informations détaillées.

## Remerciements

Un grand merci à tous les contributeurs et utilisateurs de Slot Manager. Votre soutien et vos idées sont précieux pour améliorer cet outil.
