import requests
import json

BASE_URL = 'http://localhost:5000/api'

def test_endpoint(method, endpoint, data=None):
    url = f'{BASE_URL}{endpoint}'
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        else:
            raise ValueError(f'Unsupported method: {method}')
        
        print(f'\nTesting {method} {endpoint}')
        print(f'Status Code: {response.status_code}')
        if response.text:
            try:
                print('Response:', json.dumps(response.json(), indent=2))
            except:
                print('Response:', response.text)
        return response.status_code == 200
    except Exception as e:
        print(f'Error: {str(e)}')
        return False

def main():
    # Test settings endpoints
    test_endpoint('GET', '/settings/default')
    
    # Test studies endpoints
    test_endpoint('GET', '/studies')
    
    # Create a test study
    study_data = {
        'name': 'Test Study',
        'description': 'A test study for API verification',
        'subid': 'TEST001',
        'dataset_identifier': 'TEST_DATASET'
    }
    response = test_endpoint('POST', '/studies', study_data)
    
    if response:
        # Get the study ID from the response
        study_id = response.json().get('study_id')
        if study_id:
            # Test study details
            test_endpoint('GET', f'/studies/{study_id}')
            
            # Test processing
            process_data = {
                'options': {
                    'use_prior_save': False,
                    'smooth_and_impute': True,
                    'adjust_for_gaps_and_non_wear': True,
                    'analyze_days': True,
                    'identify_curves': True
                },
                'settings': {
                    'smooth_and_impute': {
                        'reset_tac': True,
                        'median_smooth': True,
                        'impute_gaps': True
                    },
                    'curve': {
                        'curve_threshold': 0.5,
                        'periphery_buffer_before': 0.1
                    },
                    'day': {
                        'day_start_hour': 0,
                        'make_graphs': True
                    },
                    'gaps_and_non_wear': {
                        'export_excel': True
                    }
                }
            }
            test_endpoint('POST', f'/studies/{study_id}/process', process_data)
            
            # Test results endpoints
            test_endpoint('GET', f'/studies/{study_id}/days')
            test_endpoint('GET', f'/studies/{study_id}/curves')
            test_endpoint('GET', f'/studies/{study_id}/events')

if __name__ == '__main__':
    main() 