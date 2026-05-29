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
        
        stage('Deploy') {
            steps {
                script {
                    sh "docker-compose -f ${COMPOSE_FILE} down || true"
                    sh "docker-compose -f ${COMPOSE_FILE} up -d"
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
