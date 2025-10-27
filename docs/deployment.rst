Deployment
==========

This guide covers deployment strategies for the User Workspaces Server in production environments.

Production Requirements
-----------------------

System Requirements
~~~~~~~~~~~~~~~~~~~

* Linux server (Ubuntu 20.04+ or CentOS 8+ recommended)
* Python 3.10 or higher
* PostgreSQL 12+ or MySQL 8+
* Redis 6+
* Nginx (recommended reverse proxy)
* SSL/TLS certificates

Resource Requirements
~~~~~~~~~~~~~~~~~~~~~

* **Minimum**: 4 CPU cores, 8GB RAM, 100GB storage
* **Recommended**: 8+ CPU cores, 16+ GB RAM, SSD storage
* **Network**: High-bandwidth connection for file transfers

Docker Deployment
-----------------

The recommended deployment method uses Docker Compose:

1. **Clone and Configure**

   .. code-block:: bash

      git clone <repository-url>
      cd user_workspaces_server

      # Create production configuration
      cp src/example_config.json src/config.json
      cp src/example_django_config.json src/django_config.json

2. **Environment Variables**

   Create a ``.env`` file for production settings:

   .. code-block:: bash

      # Database settings
      POSTGRES_DB=userworkspaces
      POSTGRES_USER=uwsuser
      POSTGRES_PASSWORD=secure_password

      # Redis settings
      REDIS_PASSWORD=redis_password

      # Django settings
      DJANGO_SECRET_KEY=your_secret_key_here
      DJANGO_DEBUG=False
      DJANGO_ALLOWED_HOSTS=your-domain.com

3. **Deploy with Docker Compose**

   .. code-block:: bash

      # Build and start services
      docker compose -f docker-compose.prod.yml up -d

      # Run database migrations
      docker compose exec web python manage.py migrate

      # Create superuser
      docker compose exec web python manage.py createsuperuser

Traditional Deployment
----------------------

For deployment without Docker:

1. **System Preparation**

   .. code-block:: bash

      # Update system
      sudo apt update && sudo apt upgrade -y

      # Install dependencies
      sudo apt install python3.10 python3.10-venv postgresql nginx redis-server

2. **Application Setup**

   .. code-block:: bash

      # Create application user
      sudo useradd -m -s /bin/bash uwsapp

      # Clone repository
      sudo -u uwsapp git clone <repo> /home/uwsapp/user_workspaces_server

      # Set up virtual environment
      sudo -u uwsapp python3.10 -m venv /home/uwsapp/venv
      sudo -u uwsapp /home/uwsapp/venv/bin/pip install -r requirements/requirements.txt

3. **Database Configuration**

   .. code-block:: bash

      # Create database and user
      sudo -u postgres createdb userworkspaces
      sudo -u postgres createuser uwsuser
      sudo -u postgres psql -c "ALTER USER uwsuser WITH PASSWORD 'secure_password';"
      sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE userworkspaces TO uwsuser;"

4. **Application Configuration**

   Update ``django_config.json`` for production:

   .. code-block:: json

      {
        "debug": false,
        "allowed_hosts": ["your-domain.com"],
        "database": {
          "ENGINE": "django.db.backends.postgresql",
          "NAME": "userworkspaces",
          "USER": "uwsuser",
          "PASSWORD": "secure_password",
          "HOST": "localhost",
          "PORT": "5432"
        },
        "static_root": "/var/www/static/",
        "media_root": "/var/www/media/"
      }

5. **Static Files and Permissions**

   .. code-block:: bash

      # Collect static files
      sudo -u uwsapp python manage.py collectstatic --noinput

      # Set permissions
      sudo chown -R uwsapp:uwsapp /home/uwsapp/user_workspaces_server
      sudo chmod -R 755 /var/www/static
      sudo chmod -R 755 /var/www/media

Process Management
------------------

Systemd Services
~~~~~~~~~~~~~~~~

Create systemd service files for production:

**Django Application** (``/etc/systemd/system/uws-web.service``):

.. code-block:: ini

   [Unit]
   Description=User Workspaces Server Web
   After=network.target postgresql.service redis.service

   [Service]
   Type=exec
   User=uwsapp
   Group=uwsapp
   WorkingDirectory=/home/uwsapp/user_workspaces_server/src
   Environment=PATH=/home/uwsapp/venv/bin
   ExecStart=/home/uwsapp/venv/bin/python manage.py runserver 127.0.0.1:8000
   Restart=always

   [Install]
   WantedBy=multi-user.target

**Background Tasks** (``/etc/systemd/system/uws-qcluster.service``):

.. code-block:: ini

   [Unit]
   Description=User Workspaces Server Q Cluster
   After=network.target redis.service

   [Service]
   Type=exec
   User=root
   Group=root
   WorkingDirectory=/home/uwsapp/user_workspaces_server/src
   Environment=PATH=/home/uwsapp/venv/bin
   ExecStart=/home/uwsapp/venv/bin/python manage.py qcluster
   Restart=always

   [Install]
   WantedBy=multi-user.target

Enable and start services:

.. code-block:: bash

   sudo systemctl enable uws-web uws-qcluster
   sudo systemctl start uws-web uws-qcluster

Reverse Proxy Configuration
---------------------------

Nginx Configuration
~~~~~~~~~~~~~~~~~~~

Create ``/etc/nginx/sites-available/userworkspaces``:

.. code-block:: nginx

   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name your-domain.com;

       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/private.key;

       client_max_body_size 100M;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /ws/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static/ {
           alias /var/www/static/;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }

       location /media/ {
           alias /var/www/media/;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   }

Enable the site:

.. code-block:: bash

   sudo ln -s /etc/nginx/sites-available/userworkspaces /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx

Security Considerations
-----------------------

SSL/TLS Configuration
~~~~~~~~~~~~~~~~~~~~~

* Use strong SSL certificates (Let's Encrypt recommended)
* Configure secure cipher suites
* Enable HSTS headers
* Use secure session cookies

Database Security
~~~~~~~~~~~~~~~~~

* Use strong database passwords
* Configure PostgreSQL to only accept local connections
* Enable database logging for audit trails
* Regular database backups

Application Security
~~~~~~~~~~~~~~~~~~~~

* Set ``DEBUG = False`` in production
* Use a strong ``SECRET_KEY``
* Configure proper ``ALLOWED_HOSTS``
* Enable CSRF protection
* Use secure authentication tokens

Monitoring and Logging
----------------------

Log Configuration
~~~~~~~~~~~~~~~~~

Configure centralized logging in ``django_config.json``:

.. code-block:: json

   {
     "logging": {
       "version": 1,
       "handlers": {
         "file": {
           "level": "INFO",
           "class": "logging.handlers.RotatingFileHandler",
           "filename": "/var/log/uws/application.log",
           "maxBytes": 10485760,
           "backupCount": 5
         }
       },
       "loggers": {
         "user_workspaces_server": {
           "handlers": ["file"],
           "level": "INFO"
         }
       }
     }
   }

Health Checks
~~~~~~~~~~~~~

Implement health check endpoints for monitoring:

* ``/status/`` - Application health
* ``/status/database/`` - Database connectivity
* ``/status/redis/`` - Redis connectivity

Backup Strategy
---------------

Database Backups
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Daily database backup
   sudo -u postgres pg_dump userworkspaces > /backup/uws_$(date +%Y%m%d).sql

   # Automated backup script
   #!/bin/bash
   BACKUP_DIR="/backup"
   DATE=$(date +%Y%m%d_%H%M%S)
   sudo -u postgres pg_dump userworkspaces | gzip > $BACKUP_DIR/uws_$DATE.sql.gz
   find $BACKUP_DIR -name "uws_*.sql.gz" -mtime +30 -delete

File System Backups
~~~~~~~~~~~~~~~~~~~~

* Regular backups of user workspace directories
* Configuration file backups
* Application code backups

Scaling Considerations
----------------------

Horizontal Scaling
~~~~~~~~~~~~~~~~~~

* Use load balancers for multiple application instances
* Implement session store in Redis for session sharing
* Use shared storage for user workspaces (NFS, object storage)

Database Scaling
~~~~~~~~~~~~~~~~

* Configure read replicas for read-heavy workloads
* Implement connection pooling
* Monitor database performance and optimize queries

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Service Won't Start**
   * Check systemd logs: ``journalctl -u uws-web -f``
   * Verify configuration files
   * Check database connectivity

**Performance Issues**
   * Monitor resource usage: ``htop``, ``iotop``
   * Check database query performance
   * Review application logs for errors

**WebSocket Connection Issues**
   * Verify Nginx WebSocket proxy configuration
   * Check firewall rules
   * Monitor network connectivity