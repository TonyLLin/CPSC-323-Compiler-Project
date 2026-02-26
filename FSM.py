from random import randint
import time

def classify(source:str):
    # Add code here
    print("script starting")

    State = type( "State", ( object, ), {} )

    #====================================================================#
    # State Descriptions
    #====================================================================#

    class onState(State): # Should be machine on
        def Execute(self):
            print("On")

    class offState(State): # Should be machine off
        def Execute(self):
            print("Off")

    #====================================================================#
    # Transitions
    #====================================================================#

    class Transition( object ): # Transitioning between on and off states
        def __init__(self, toState):
            self.toState = toState

        def Execute(self):
            print("Transitioning states")
    

#====================================================================#
# States
#====================================================================#

    class myFSM(object):
        def __init__(self, char):
            self.char = char
            self.states = {}
            self.transitions = {}
            self.curState = None # define what state FSM is in
            self.trans = None   # define if FSM is switching states

        def setState(self, stateName):
            self.curState = self.states[stateName] # make sure state we pass in is inside of dictionary above then set it

        def Transition(self, transName):
            self.trans = self.transitions[transName] # make sure transition is inside of the library as well

        def Execute(self):
            if self.trans:
                self.trans.Execute() # if transition stored in library, execute that transition
                self.setState(self.trans.toState) # then set state to that transition
                self.trans = None # reset the transition to none as we already set new state
            self.curState.Execute()
    
    class Char(object):
        def __init__(self):
            self.FSM = myFSM(self) # create instance of FSM
            self.onState = True # turning it on


    # Another example from demo
    # gives idea of having multiple states and what we could do with that
    '''
    class CleanDishes(State):
        def __init__(self, FSM):
            super(CleanDishes, self).__init__(FSM)
        
        def Enter(self):
            print ("Doing the Dishes")
            super(CleanDishes, self).Enter()

        def Execute(self):
            print ("Cleaning Dishes")
            if(self.startTime + self.timer <= time.perf_counter()):
                if not( randint(1,3) % 2):
                    self.FSM.ToTransition("toVacuum")
                else:
                    self.FSM.toTransition("toSleep")
        
        def Exit(self):
            print("Finished cleaning dishes.")
    '''

    light = Char() # light is placeholder name used in the demo. Can change it to something more suitable

    light.FSM.states["On"] = onState() # create instance of onState & store it inside state disctionary
    light.FSM.states["Off"] = offState() # create instance of offState & store it inside state disctionary
    light.FSM.transitions["toOn"] = Transition("On") # create instance of transition & store it inside transition dictionary
    light.FSM.transitions["toOff"] = Transition("Off") # create instance of transition & store it inside transition dictionary

    light.FSM.setState("On")

    for i in range(20):   # Demo of states changing with random. 
        startTime = time.perf_counter() 
        timeInterval = 1
        while (startTime + timeInterval > time.perf_counter()):
            pass
        if randint(0,1):
            if(light.onState):
                light.FSM.Transition("toOff")
                light.onState = False
            else:
                light.FSM.Transition("toOn")
                light.onState = True
        light.FSM.Execute()

    return ("To be classified", source)

classify("some source")