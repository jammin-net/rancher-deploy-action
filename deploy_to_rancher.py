import os
import sys
import platform

# Add diagnostic logging
print(f"Python version: {platform.python_version()}")
print(f"Python implementation: {platform.python_implementation()}")
print(f"Python version info: {sys.version_info}")
print(f"Python version string: {sys.version}")

try:
    import requests
    print(f"Requests version: {requests.__version__}")
except ImportError as e:
    print(f"Failed to import requests: {e}")
except Exception as e:
    print(f"Error importing requests: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Original imports
import os
import sys
import requests


class DeployRancher:
    def __init__(self, rancher_access_key, rancher_secret_key, rancher_url_api,
                 rancher_service_name, rancher_docker_image, default_project=None, default_namespace=None):
        self.access_key = rancher_access_key
        self.secret_key = rancher_secret_key
        self.rancher_url_api = rancher_url_api
        self.service_name = rancher_service_name
        self.docker_image = rancher_docker_image
        self.default_project = default_project
        self.default_namespace = default_namespace
        self.rancher_deployment_path = ''
        self.rancher_namespace = ''
        self.rancher_workload_url_api = ''

    def deploy(self):
        print(f"Deploying {self.docker_image} to service {self.service_name}")
        print(f"Calling Rancher API at: {self.rancher_url_api}/projects")
        
        try:
            rp = requests.get('{}/projects'.format(self.rancher_url_api), auth=(self.access_key, self.secret_key))
            print(f"Projects API response status: {rp.status_code}")
            if rp.status_code != 200:
                print(f"Error response: {rp.text}")
                sys.exit(1)
            
            projects = rp.json()
            if 'data' not in projects:
                print(f"Missing 'data' key in projects response. Response structure: {list(projects.keys())}")
                print(f"Full response: {projects}")
                sys.exit(1)
            
            print(f"Found {len(projects['data'])} projects")
            
            for p in projects['data']:
                print(f"Checking project: {p.get('name', 'Unknown')} (ID: {p.get('id', 'Unknown')})")
                w_url = '{}/projects/{}/workloads'.format(self.rancher_url_api, p['id'])
                print(f"Calling workloads API at: {w_url}")
                
                rw = requests.get(w_url, auth=(self.access_key, self.secret_key))
                print(f"Workloads API response status: {rw.status_code}")
                if rw.status_code != 200:
                    print(f"Error response: {rw.text}")
                    continue
                
                workload = rw.json()
                if 'data' not in workload:
                    print(f"Missing 'data' key in workload response. Response structure: {list(workload.keys())}")
                    continue
                
                print(f"Found {len(workload['data'])} workloads in project")
                
                for w in workload['data']:
                    if w['name'] == self.service_name:
                        print(f"Found service {self.service_name} in project")
                        self.rancher_workload_url_api = w_url
                        self.rancher_deployment_path = w['links']['self']
                        self.rancher_namespace = w['namespaceId']
                        break
                if self.rancher_deployment_path != '':
                    break

            # If a specific project name is set, try to find it first
            target_project = None
            if self.default_project:
                print(f"Looking for specified default project: {self.default_project}")
                for p in projects['data']:
                    if p.get('name') == self.default_project:
                        target_project = p
                        print(f"Found default project: {p.get('name')} (ID: {p.get('id')})")
                        break

            if self.rancher_deployment_path == '':
                print(f"Service {self.service_name} not found in any project")
                
                # Use specific project if set, otherwise first project
                project_to_use = target_project if target_project else (projects['data'][0] if len(projects['data']) > 0 else None)
                
                if project_to_use:
                    print(f"Creating new service in project: {project_to_use['name']}")
                    project_id = project_to_use['id']
                    
                    # Get namespaces in this project
                    namespaces_url = f"{self.rancher_url_api}/projects/{project_id}/namespaces"
                    rn = requests.get(namespaces_url, auth=(self.access_key, self.secret_key))
                    print(f"Namespaces API response status: {rn.status_code}")
                    
                    namespaces = rn.json()
                    if 'data' not in namespaces or len(namespaces['data']) == 0:
                        print("No namespaces found to create workload")
                        sys.exit(1)
                    
                    # Try to find the specific namespace if specified
                    namespace_to_use = None
                    if self.default_namespace:
                        print(f"Looking for specified default namespace: {self.default_namespace}")
                        for ns in namespaces['data']:
                            if ns.get('name') == self.default_namespace:
                                namespace_to_use = ns
                                print(f"Found default namespace: {ns.get('name')} (ID: {ns.get('id')})")
                                break
                    
                    # Use found namespace or fall back to first one
                    if not namespace_to_use and len(namespaces['data']) > 0:
                        namespace_to_use = namespaces['data'][0]
                    
                    namespace_id = namespace_to_use['id']
                    print(f"Using namespace: {namespace_to_use.get('name')} (ID: {namespace_id})")
                    
                    # Set workload API URL
                    self.rancher_workload_url_api = f"{self.rancher_url_api}/projects/{project_id}/workloads"
                    self.rancher_namespace = namespace_id
                    
                    # Now create config and deploy
                    config = {
                        "containers": [{
                            "imagePullPolicy": "Always",
                            "image": self.docker_image,
                            "name": self.service_name,
                        }],
                        "namespaceId": namespace_id,
                        "name": self.service_name
                    }
                    
                    print(f"Creating new workload with config: {config}")
                    result = requests.post(self.rancher_workload_url_api,
                                json=config, auth=(self.access_key, self.secret_key))
                    print(f"Create response: {result.status_code} - {result.text}")
                    print(f"Deployment of {self.docker_image} as new service {self.service_name} completed")
                    sys.exit(0)
                else:
                    print("No projects available to create service in")
                    sys.exit(1)

            print(f"Getting deployment details from: {self.rancher_deployment_path}")
            rget = requests.get(self.rancher_deployment_path,
                              auth=(self.access_key, self.secret_key))
            print(f"Deployment API response status: {rget.status_code}")
            
            response = rget.json()
            
            if 'status' in response and response['status'] == 404:
                print(f"Creating new deployment for {self.service_name}")
                config = {
                    "containers": [{
                        "imagePullPolicy": "Always",
                        "image": self.docker_image,
                        "name": self.service_name,
                    }],
                    "namespaceId": self.rancher_namespace,
                    "name": self.service_name
                }
                
                result = requests.post(self.rancher_workload_url_api,
                            json=config, auth=(self.access_key, self.secret_key))
                print(f"Create response: {result.status_code} - {result.text}")
            else:
                print(f"Updating existing deployment for {self.service_name}")
                if 'containers' not in response or not response['containers']:
                    print(f"Missing containers in response: {response}")
                    sys.exit(1)
                    
                response['containers'][0]['image'] = self.docker_image
                
                result = requests.put(self.rancher_deployment_path + '?action=redeploy',
                           json=response, auth=(self.access_key, self.secret_key))
                print(f"Update response: {result.status_code} - {result.text}")
                
            print(f"Deployment of {self.docker_image} to {self.service_name} completed")
            sys.exit(0)
            
        except Exception as e:
            print(f"Error during deployment: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def deploy_in_rancher(rancher_access_key, rancher_secret_key, rancher_url_api,
                      rancher_service_name, rancher_docker_image,
                      default_project=None, default_namespace=None):
    deployment = DeployRancher(rancher_access_key, rancher_secret_key, rancher_url_api,
                               rancher_service_name, rancher_docker_image,
                               default_project, default_namespace)
    deployment.deploy()


if __name__ == '__main__':
    print("Starting Rancher deployment")
    rancher_access_key = os.environ['RANCHER_ACCESS_KEY']
    rancher_secret_key = os.environ['RANCHER_SECRET_KEY']
    rancher_url_api = os.environ['RANCHER_URL_API']
    rancher_service_name = os.environ['SERVICE_NAME']
    rancher_docker_image = os.environ['DOCKER_IMAGE']
    rancher_docker_image_latest = os.environ['DOCKER_IMAGE_LATEST']
    
    # Get optional default project/namespace
    default_project = os.environ.get('DEFAULT_PROJECT', None)
    default_namespace = os.environ.get('DEFAULT_NAMESPACE', None)
    
    print(f"Environment variables loaded:")
    print(f"API URL: {rancher_url_api}")
    print(f"Service Name: {rancher_service_name}")
    print(f"Docker Image: {rancher_docker_image}")
    print(f"Docker Image Latest: {rancher_docker_image_latest}")
    if default_project:
        print(f"Default Project: {default_project}")
    if default_namespace:
        print(f"Default Namespace: {default_namespace}")
    
    try:
        deploy_in_rancher(rancher_access_key, rancher_secret_key, rancher_url_api,
                          rancher_service_name, rancher_docker_image, 
                          default_project, default_namespace)
        
        if rancher_docker_image_latest != None and rancher_docker_image_latest != "":
            deploy_in_rancher(rancher_access_key, rancher_secret_key, rancher_url_api, 
                              rancher_service_name, rancher_docker_image_latest,
                              default_project, default_namespace)

    except Exception as e:
        print(f"Error in main: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)