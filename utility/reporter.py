import os
from datetime import datetime
from collections import defaultdict

class TestReporter:
    def __init__(self):
        self.features = defaultdict(dict)
        self.current_feature = None
        self.current_scenario = None
        self.current_step = None
        
    def start_feature(self, feature_name):
        """Record the start of a feature"""
        self.current_feature = feature_name
        self.features[feature_name] = {
            'scenarios': defaultdict(dict),
            'start_time': datetime.now(),
            'status': 'passed'
        }

    def end_feature(self, feature_name, duration):
        """Record the end of a feature"""
        self.features[feature_name]['duration'] = duration
        # Feature fails if any scenario failed
        for scenario in self.features[feature_name]['scenarios'].values():
            if scenario['status'] == 'failed':
                self.features[feature_name]['status'] = 'failed'
                break

    def start_scenario(self, scenario_name):
        """Record the start of a scenario"""
        self.current_scenario = scenario_name
        self.features[self.current_feature]['scenarios'][scenario_name] = {
            'steps': defaultdict(dict),
            'start_time': datetime.now(),
            'status': 'passed'
        }

    def end_scenario(self, scenario_name, status, duration):
        """Record the end of a scenario"""
        self.features[self.current_feature]['scenarios'][scenario_name].update({
            'status': status,
            'duration': duration
        })

    def start_step(self, step_name):
        """Record the start of a step"""
        self.current_step = step_name
        self.features[self.current_feature]['scenarios'][self.current_scenario]['steps'][step_name] = {
            'start_time': datetime.now(),
            'status': 'pending'
        }

    def end_step(self, step_name, status, duration, error_message=None):
        """Record the end of a step"""
        step_data = {
            'status': status,
            'duration': duration
        }
        if error_message:
            step_data['error_message'] = error_message
        
        self.features[self.current_feature]['scenarios'][self.current_scenario]['steps'][step_name].update(step_data)
        
        # If step failed, mark scenario as failed
        if status == 'failed':
            self.features[self.current_feature]['scenarios'][self.current_scenario]['status'] = 'failed'

    def generate_report(self, output_file):
        """Generate HTML report from collected test data"""
        html = self._get_report_header()
        
        # Summary section
        total_features = len(self.features)
        passed_features = sum(1 for f in self.features.values() if f['status'] == 'passed')
        total_scenarios = sum(len(f['scenarios']) for f in self.features.values())
        passed_scenarios = sum(
            sum(1 for s in f['scenarios'].values() if s['status'] == 'passed')
            for f in self.features.values()
        )
        
        html += f'''
        <div class="summary">
            <h2>Test Execution Summary</h2>
            <p>Features: {passed_features}/{total_features} passed</p>
            <p>Scenarios: {passed_scenarios}/{total_scenarios} passed</p>
        </div>
        '''
        
        # Feature details
        for feature_name, feature_data in self.features.items():
            status_class = 'passed' if feature_data['status'] == 'passed' else 'failed'
            duration = feature_data['duration'].total_seconds()
            
            html += f'''
            <div class="feature {status_class}">
                <h2>Feature: {feature_name}</h2>
                <p>Status: {feature_data['status']}</p>
                <p>Duration: {duration:.2f}s</p>
                
                <div class="scenarios">
            '''
            
            # Scenario details
            for scenario_name, scenario_data in feature_data['scenarios'].items():
                status_class = 'passed' if scenario_data['status'] == 'passed' else 'failed'
                duration = scenario_data['duration'].total_seconds()
                
                html += f'''
                <div class="scenario {status_class}">
                    <h3>Scenario: {scenario_name}</h3>
                    <p>Status: {scenario_data['status']}</p>
                    <p>Duration: {duration:.2f}s</p>
                    
                    <div class="steps">
                '''
                
                # Step details
                for step_name, step_data in scenario_data['steps'].items():
                    status_class = step_data['status'].lower()
                    duration = step_data['duration'].total_seconds()
                    
                    html += f'''
                    <div class="step {status_class}">
                        <p>{step_name}</p>
                        <p>Status: {step_data['status']}</p>
                        <p>Duration: {duration:.2f}s</p>
                    '''
                    
                    if 'error_message' in step_data:
                        html += f'''
                        <div class="error">
                            <pre>{step_data['error_message']}</pre>
                        </div>
                        '''
                    
                    html += '</div>'  # Close step
                
                html += '</div></div>'  # Close steps and scenario
            
            html += '</div></div>'  # Close scenarios and feature
        
        html += self._get_report_footer()
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write the report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def _get_report_header(self):
        """Returns the HTML header with CSS styling"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>BDD Test Execution Report</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .summary {
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .feature {
                    background-color: #fff;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .scenario {
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 3px;
                    background-color: #f9f9f9;
                }
                .step {
                    margin: 5px 0;
                    padding: 5px 10px;
                    border-left: 4px solid #ccc;
                }
                .passed {
                    border-color: #4CAF50;
                }
                .failed {
                    border-color: #f44336;
                }
                .pending {
                    border-color: #FFC107;
                }
                .error {
                    background-color: #ffebee;
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 3px;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    margin: 0;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <h1>BDD Test Execution Report</h1>
        '''

    def _get_report_footer(self):
        """Returns the HTML footer"""
        return '''
        </body>
        </html>
        '''
