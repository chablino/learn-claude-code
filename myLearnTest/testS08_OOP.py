class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        self.friends = []

    def add_friend(self, friend):
        self.friends.append(friend) 

    def __str__(self):
        return f"Person(name={self.name}, age={self.age}, friends={[friend.name for friend in self.friends]})"
    def __repr__(self):
        return f"Person('{self.name}', {self.age})"
    
# 创建一个人
alice = Person("Alice", 30)
# 创建另一个人
bob = Person("Bob", 25)
# 让他们成为朋友
alice.add_friend(bob)
bob.add_friend(alice)
# 打印他们的信息
friends = [alice, bob]
print(friends)