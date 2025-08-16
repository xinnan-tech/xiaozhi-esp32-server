#!/usr/bin/env python3
"""
Test script for concurrent client connections to Zipformer Streaming English ASR
Usage: python test_concurrent_clients.py
"""

import asyncio
import websockets
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

class ConcurrentASRTester:
    def __init__(self, server_url="ws://localhost:8000/xiaozhi/v1/"):
        self.server_url = server_url
        self.results = []
        self.lock = threading.Lock()

    async def single_client_test(self, client_id, test_duration=10):
        """Simulate a single client connection"""
        try:
            async with websockets.connect(self.server_url) as websocket:
                start_time = time.time()
                requests_sent = 0
                responses_received = 0
                
                print(f"Client {client_id}: Connected")
                
                # Send test messages for specified duration
                while time.time() - start_time < test_duration:
                    # Send a test audio message (mock)
                    test_message = {
                        "type": "audio",
                        "data": "test_audio_data",
                        "session_id": f"client_{client_id}_{requests_sent}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    requests_sent += 1
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        responses_received += 1
                    except asyncio.TimeoutError:
                        print(f"Client {client_id}: Timeout waiting for response")
                    
                    await asyncio.sleep(0.5)  # Simulate natural speech pauses
                
                with self.lock:
                    self.results.append({
                        'client_id': client_id,
                        'requests_sent': requests_sent,
                        'responses_received': responses_received,
                        'success_rate': responses_received / requests_sent if requests_sent > 0 else 0,
                        'duration': time.time() - start_time
                    })
                
                print(f"Client {client_id}: Completed - {requests_sent} requests, {responses_received} responses")
                
        except Exception as e:
            print(f"Client {client_id}: Error - {e}")
            with self.lock:
                self.results.append({
                    'client_id': client_id,
                    'error': str(e)
                })

    async def run_concurrent_test(self, num_clients=5, test_duration=10):
        """Run concurrent client tests"""
        print(f"Starting concurrent test with {num_clients} clients for {test_duration} seconds each")
        
        # Create tasks for all clients
        tasks = []
        for i in range(num_clients):
            task = asyncio.create_task(self.single_client_test(i + 1, test_duration))
            tasks.append(task)
        
        # Wait for all clients to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Print results
        self.print_results()

    def print_results(self):
        """Print test results"""
        print("\n" + "="*60)
        print("CONCURRENT CLIENT TEST RESULTS")
        print("="*60)
        
        successful_clients = [r for r in self.results if 'error' not in r]
        failed_clients = [r for r in self.results if 'error' in r]
        
        if successful_clients:
            total_requests = sum(r['requests_sent'] for r in successful_clients)
            total_responses = sum(r['responses_received'] for r in successful_clients)
            avg_success_rate = sum(r['success_rate'] for r in successful_clients) / len(successful_clients)
            
            print(f"Successful Clients: {len(successful_clients)}")
            print(f"Failed Clients: {len(failed_clients)}")
            print(f"Total Requests Sent: {total_requests}")
            print(f"Total Responses Received: {total_responses}")
            print(f"Overall Success Rate: {total_responses/total_requests*100:.1f}%")
            print(f"Average Client Success Rate: {avg_success_rate*100:.1f}%")
            
            print("\nPer-Client Results:")
            for result in successful_clients:
                print(f"  Client {result['client_id']}: {result['success_rate']*100:.1f}% success rate")
        
        if failed_clients:
            print(f"\nFailed Clients: {len(failed_clients)}")
            for result in failed_clients:
                print(f"  Client {result['client_id']}: {result['error']}")

def main():
    """Main test function"""
    tester = ConcurrentASRTester()
    
    print("Testing Zipformer Streaming English ASR with multiple concurrent clients")
    print("Make sure your server is running with SherpaZipformerStreamingEN selected")
    
    # Test different client loads
    test_scenarios = [
        (2, 10),   # 2 clients for 10 seconds
        (5, 10),   # 5 clients for 10 seconds  
        (10, 10),  # 10 clients for 10 seconds
    ]
    
    for num_clients, duration in test_scenarios:
        print(f"\n{'='*60}")
        print(f"TESTING: {num_clients} concurrent clients")
        print(f"{'='*60}")
        
        asyncio.run(tester.run_concurrent_test(num_clients, duration))
        tester.results.clear()  # Clear results for next test
        
        input("Press Enter to continue to next test...")

if __name__ == "__main__":
    main()