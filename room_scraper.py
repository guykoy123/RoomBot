import random

class room:
    id_counter=0
    def __init__(self,room_number,available_times,size):
        self.number = room_number
        self.available_times=available_times
        self.size = size
        self.id = room.id_counter
        room.id_counter+=1

    def TimeToString(self):
        display=""
        for t in self.available_times:
            display += t.__start__+":"+t.__end__+", "

class time_slot:
    id_counter=0
    def __init__(self,start,end):
        self.start=start
        self.end=end
        self.id = time_slot.id_counter
        time_slot.id_counter+=1

class schedule:
    sunday=time_slot(14,19)
    monday=time_slot(16,19)
    tuesday=time_slot(12,17)
    wednesday=time_slot(13,20)
    thursday=time_slot(15,18)
        

def get_available_rooms():
    available_rooms=[]
    for i in range(5):
        times=[]
        temp=random.randint(1,3)
        for j in range(temp):
            start=random.randint(9,18)
            t=time_slot(start,start+2)
            times.append(t)
        r = room(400+i,times,random.randint(0,2))
        available_rooms.append(r)
    return available_rooms
