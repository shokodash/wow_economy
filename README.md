# Introduction

This is a site that tracks the average price of World of Warcraft auction items.
The cron job pulls the auctions and processes them for the frontend.

# Installation

## Requires:
 - Python 2.7+
 - SQLAlchemy
 - A database (I use postgresql, you can use whatever, just alter the models.py connection URI)

## Preparation

It is recommended to use _virtualenv_ for development:

 - Run: _virtualenv -p /usr/bin/python2 venv_
 - _source venv/bin/activate_
 - _pip install -r REQUIRES_

You will need a PostgreSQL database on your system. If you can run _psql_ command on your system, then the PostgreSQL is installed. If not, here you can find some instructions on how to install the database system on your machine: https://wiki.postgresql.org/wiki/Detailed_installation_guides.

Assuming you work on _localhost_ and you have not created a database yet. Then:

 - Run: _psql_
 - _CREATE DATABASE wow_economy;_
 - _\q_
 - Test the database by running: _psql wow_economy_. If you could connect successfully, then the database is ready.
 - Open the file _src/models.py_ and modify the line with _create_engine()_ so that it matches the username and password of your system and the given database.

## Deployment

 - First time run _src/models.py_.
 - After that run _src/auction_cron.py_, which will download initial data from API Battle.net. If it works, you are safe to schedule a cron job on Linux.
 - ( **on Linux ONLY** ) set-up the cron job to run _src/auction_cron.py_ every 30 minutes.
 - Start the web server by running _python src/web.py_.


# Info

This project was forked from: https://github.com/shokodash/wow_economy

