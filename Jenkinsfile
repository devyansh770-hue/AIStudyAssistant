pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "toto749/studyai:latest"
        COMPOSE_FILE = "docker-compose.yml"
    }

    stages {
        stage('Pull Image') {
            steps {
                script {
                    sh "docker pull ${DOCKER_IMAGE}"
                }
            }
        }
        
        stage('Test') {
            steps {
                script {
                    sh "docker run --rm -e SECRET_KEY=dummy-test-key -e DEBUG=True -e DATABASE_URL='' ${DOCKER_IMAGE} python manage.py test"
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    sh '''
                    echo 'DEBUG=True' > .env
                    echo 'SECRET_KEY=django-insecure-dev-key-for-local-development' >> .env
                    echo 'ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0' >> .env
                    echo 'GEMINI_API_KEY=AIzaSyAXXn4ied-qXu8sMUhSMXJTNsoFnGQYp-w' >> .env

                    '''
                    sh "docker-compose -f ${COMPOSE_FILE} down || true"
                    sh "docker-compose -f ${COMPOSE_FILE} up -d"
                    sh "docker-compose -f ${COMPOSE_FILE} exec -T web python manage.py migrate"
                }
            }
        }

        stage('Cleanup') {
            steps {
                script {
                    sh "docker image prune -f"
                }
            }
        }
    }

    post {
        success {
            echo 'Deployment Successful!'
        }
        failure {
            echo 'Deployment Failed!'
        }
    }
}
