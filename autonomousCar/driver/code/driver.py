import logging
import picar
import cv2
import datetime
from lane_detection_follower import LaneDetectionFollower
from intersect_detection import IntersectDetection
from ml_follower_tpu import MLFollower
from tpu_processor import TPUProcessor

_SHOW_IMAGE = True


class DeepPiCar(object):

    __INITIAL_SPEED = 0
    __SCREEN_WIDTH = 320
    __SCREEN_HEIGHT = 240

    def __init__(self):
        """ Init camera and wheels"""
        logging.info('Creating a DeepPiCar...')

        picar.setup()

        logging.debug('Set up camera')
        self.camera = cv2.VideoCapture(-1)
        self.camera.set(3, self.__SCREEN_WIDTH)
        self.camera.set(4, self.__SCREEN_HEIGHT)

        self.pan_servo = picar.Servo.Servo(1)
        self.pan_servo.offset = 0  # calibrate servo to center
        self.pan_servo.write(90)

        self.tilt_servo = picar.Servo.Servo(2)
        self.tilt_servo.offset = 0  # calibrate servo to center
        self.tilt_servo.write(90)

        logging.debug('Set up back wheels')
        self.back_wheels = picar.back_wheels.Back_Wheels()
        self.back_wheels.speed = 0  # Speed Range is 0 (stop) - 100 (fastest)

        logging.debug('Set up front wheels')
        self.front_wheels = picar.front_wheels.Front_Wheels()
        self.front_wheels.turning_offset = 00  # calibrate servo to center
        self.front_wheels.turn(90)  # Steering Range is 45 (left) - 90 (center) - 135 (right)
        
        self.tpu_processor = TPUProcessor(self)
        self.intersect = IntersectDetection(self)      		
        self.lane_follower = LaneDetectionFollower(self)
#         self.lane_follower = MLFollower(self)

        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        datestr = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        self.video_orig = self.create_video_recorder('../data/video03.avi')
        self.video_lane = self.create_video_recorder('../data/car_video_lane%s.avi' % datestr)
        self.video_objs = self.create_video_recorder('../data/car_video_objs%s.avi' % datestr)

        logging.info('Created a DeepPiCar')

    def create_video_recorder(self, path):
        return cv2.VideoWriter(path, self.fourcc, 20.0, (self.__SCREEN_WIDTH, self.__SCREEN_HEIGHT))

    def __enter__(self):
        """ Entering a with statement """
        return self

    def __exit__(self, _type, value, traceback):
        """ Exit a with statement"""
        if traceback is not None:
            # Exception occurred:
            logging.error('Exiting with statement with exception %s' % traceback)

        self.cleanup(self.i, self.first_time)

    def cleanup(self, steering_num, first_time):
        """ Reset the hardware"""
        logging.info('Stopping the car, resetting hardware.')
        self.back_wheels.speed = 0
        self.front_wheels.turn(90)
        self.camera.release()
        self.video_orig.release()
        self.video_lane.release()
        self.video_objs.release()
        last_time = datetime.datetime.now()
        diff = last_time - first_time
        diff = float(diff.total_seconds())
        logging.info("steers: " + str(steering_num))
        logging.info("time: " + str(diff))
        logging.info("steers per min: " + str(steering_num/diff))
        cv2.destroyAllWindows()

    def drive(self, speed=__INITIAL_SPEED):
        """ Main entry point of the car, and put it in drive mode

        Keyword arguments:
        speed -- speed of back wheel, range is 0 (stop) - 100 (fastest)
        """
        logging.info('Starting to drive at speed %s...' % speed)
        self.back_wheels.forward()
        self.back_wheels.speed = speed
        self.i = 0
        self.first_time = datetime.datetime.now()
        intersect_count = 0
        while self.camera.isOpened():
        	_, image_lane = self.camera.read()
        	image_objs = image_lane.copy()
        	self.i += 1
        	self.video_orig.write(image_lane)
        	is_intersect = self.detect_intersect(image_lane)
        	logging.debug("intersect: " + str(is_intersect))
        	if is_intersect:
        		intersect_count += 1
        		if intersect_count >= 3: # there is an intersection detected
        			# todo: go through the list of turns / where to import the list?
        			self.intersection_turn(image_lane, [1, 0, 0, -1, 0]) # todo: change fixed list
        			intersect_count = 0
        			continue
        	else: # there is no intersection detected
        		intersect_count = 0
        		image_lane = self.follow_lane(image_lane)
        	self.video_lane.write(image_lane)
        	show_image('Lane Lines', image_lane)
        	
        	if cv2.waitKey(1) & 0xFF == ord('q'):
        		self.cleanup(self.i, self.first_time)
        		break

    def process_objects_on_road(self, image):
        image = self.traffic_sign_processor.process_objects_on_road(image)
        return image

    def follow_lane(self, image):
        image = self.lane_follower.follow_lane(image)
        return image
        
    def detect_intersect(self, image):
        image = self.intersect.detect_intersect(image)
        return image
    
    def intersection_turn(self, image, turns):
    	turn_magnitude = 45
    	turn = turns.pop(0)
    	turn_time = 5
    	s_diff = 0
    	start_time = datetime.datetime.now()
    	
    	while s_diff < turn_time:
    		cnt_time = datetime.datetime.now()
    		diff = cnt_time - start_time
    		s_diff = diff.seconds
    		
    		if turn == -1:
    			self.front_wheels.turn(90 - turn_magnitude)
    		elif turn == 0:
    			self.front_wheels.turn(90)
    		else:
    			self.front_wheels.turn(90 + turn_magnitude)
    			
    	return image
    		

def show_image(title, frame, show=_SHOW_IMAGE):
    if show:
        cv2.imshow(title, frame)


def main():
    with DeepPiCar() as car:
        car.drive(25)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-5s:%(asctime)s: %(message)s')
    
    main()
