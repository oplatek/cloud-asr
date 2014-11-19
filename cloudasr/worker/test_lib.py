import unittest
import config
from lib import Worker, Heartbeat
from cloudasr.messages.helpers import *
from cloudasr.test_doubles import PollerSpy, SocketSpy


class TestWorker(unittest.TestCase):

    def setUp(self):
        self.model = "en-GB"
        self.worker_address = "tcp://127.0.0.1:5678"
        self.master_socket = SocketSpy()
        self.saver = SaverSpy()

        self.heartbeat = Heartbeat(self.model, self.worker_address, self.master_socket)
        self.poller = PollerSpy()
        self.asr = ASRSpy([(1.0, "Hello World!")], (1.0, "Interim result"))
        self.audio = DummyAudio()
        self.worker = Worker(self.poller, self.heartbeat, self.asr, self.audio, self.saver, self.poller.has_next_message)

    def test_worker_forwards_wav_from_every_message_to_asr_as_pcm(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1")},
            {"frontend": self.make_frontend_request("message 2")}
        ]

        self.run_worker(messages)
        self.assertThatAsrProcessedChunks(["pcm message 1", "pcm message 2"])

    def test_worker_reads_final_hypothesis_from_asr(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1")},
            {"frontend": self.make_frontend_request("message 2")}
        ]

        self.run_worker(messages)
        expected_message = createResultsMessage(True, [(1.0, "Hello World!")])
        self.assertThatMessagesWereSendToFrontend([expected_message, expected_message])

    def test_worker_sends_interim_results_after_each_chunk(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE")},
            {"frontend": self.make_frontend_request("message 2", "ONLINE")}
        ]

        self.run_worker(messages)
        expected_message = createResultsMessage(False, [(1.0, "Interim result")])
        self.assertThatMessagesWereSendToFrontend([expected_message, expected_message])

    def test_worker_sends_final_results_after_last_chunk(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = False)}
        ]

        self.run_worker(messages)
        expected_message1 = createResultsMessage(False, [(1.0, "Interim result")])
        expected_message2 = createResultsMessage(True, [(1.0, "Hello World!")])
        self.assertThatMessagesWereSendToFrontend([expected_message1, expected_message2])

    def test_when_worker_receives_chunk_with_bad_id_it_should_return_error_message(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True, id = 1)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = True, id = 2)},
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = False, id = 1)},
        ]

        self.run_worker(messages)
        expected_message1 = createResultsMessage(False, [(1.0, "Interim result")])
        expected_message2 = createErrorResultsMessage()
        expected_message3 = createResultsMessage(True, [(1.0, "Hello World!")])
        self.assertThatMessagesWereSendToFrontend([expected_message1, expected_message2, expected_message3])

    def test_worker_forwards_resampled_pcm_chunks_from_every_message_to_asr(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = True)}
        ]

        self.run_worker(messages)
        self.assertThatAsrProcessedChunks(["resampled message 1", "resampled message 2"])

    def test_worker_sends_heartbeat_to_master_when_ready_to_work(self):
        messages = []
        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING"])

    def test_worker_sends_heartbeat_after_finishing_task(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1")}
        ]

        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING", "FINISHED"])

    def test_worker_sends_working_heartbeats_during_online_recognition(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = False)}
        ]

        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING", "WORKING", "WORKING", "FINISHED"])

    def test_worker_sends_finished_heartbeat_after_end_of_online_recognition(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", has_next = False)}
        ]

        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING", "WORKING", "FINISHED"])

    def test_worker_sends_finished_heartbeat_when_it_doesnt_receive_any_chunk_for_10secs(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", has_next = True)},
            {"time": +10}
        ]

        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING", "WORKING", "FINISHED"])

    def test_worker_sends_ready_heartbeat_when_it_doesnt_receive_any_task(self):
        messages = [{}]
        self.run_worker(messages)
        self.assertThatHeartbeatsWereSent(["RUNNING", "READY"])

    def test_worker_saves_pcm_data_from_batch_request(self):
        messages = [
            {"frontend": self.make_frontend_request("message", "BATCH", id = 1, has_next = False)},
        ]

        self.run_worker(messages)
        self.assertThatDataWasStored({
            1: {"pcm": "pcm message", "hypothesis": [(1.0, "Hello World!")]}
        })

    def test_worker_saves_pcm_data_from_online_request(self):
        messages = [
            {"frontend": self.make_frontend_request("message 1", "ONLINE", id = 1, has_next = True)},
            {"frontend": self.make_frontend_request("message 2", "ONLINE", id = 1, has_next = True)},
            {"frontend": self.make_frontend_request("message 3", "ONLINE", id = 1, has_next = False)},
        ]

        self.run_worker(messages)
        self.assertThatDataWasStored({
            1: {"pcm": "resampled message 1resampled message 2resampled message 3", "hypothesis": [(1.0, "Hello World!")]}
        })

    def run_worker(self, messages):
        self.poller.add_messages(messages)
        self.worker.run()

    def assertThatAsrProcessedChunks(self, chunks):
        self.assertEquals(chunks, self.asr.processed_chunks)

    def assertThatMessagesWereSendToFrontend(self, messages):
        sent_messages = [parseResultsMessage(message) for message in self.poller.sent_messages["frontend"]]
        self.assertEquals(messages, sent_messages)

    def assertThatHeartbeatsWereSent(self, heartbeats):
        heartbeats = [self.make_heartbeat(state) for state in heartbeats]
        sent_heartbeats = [parseHeartbeatMessage(message) for message in self.master_socket.sent_messages]

        self.assertEquals(heartbeats, sent_heartbeats)

    def assertThatDataWasStored(self, data):
        self.assertEquals(data, self.saver.saved_data)

    def make_frontend_request(self, message, type = "BATCH", has_next = True, id = 0):
        return createRecognitionRequestMessage(type, message, has_next, id, 44100).SerializeToString()

    def make_heartbeat(self, status):
        return createHeartbeatMessage(self.worker_address, self.model, status)

class ASRSpy:

    def __init__(self, final_hypothesis, interim_hypothesis):
        self.processed_chunks = []
        self.final_hypothesis = final_hypothesis
        self.interim_hypothesis = interim_hypothesis

    def recognize_chunk(self, chunk):
        self.processed_chunks.append(chunk)

        return self.interim_hypothesis

    def get_final_hypothesis(self):
        return self.final_hypothesis


class DummyAudio:

    def load_wav_from_string_as_pcm(self, string):
        return "pcm " + string

    def resample_to_default_sample_rate(self, pcm, sample_rate):
        return "resampled " + pcm

class SaverSpy:

    def __init__(self):
        self.saved_data = {}

    def new_recognition(self, id):
        self.id = self.parse_id(id)
        self.saved_data[self.id] = {"pcm": "", "hypothesis": ""}

    def add_pcm(self, pcm):
        self.saved_data[self.id]["pcm"] += pcm

    def final_hypothesis(self, final_hypothesis):
        self.saved_data[self.id]["hypothesis"] = final_hypothesis

    def parse_id(self, id):
        return int(id.upper << 64 | id.lower)
