import os

def deleteMemories():
    print("deleting memories; plase hold on")
    if os.path.exists("Nova/nova_logs/nova_log.txt"):
        
        os.remove("Nova/nova_logs/nova_log.txt")
        print("Memories1 deleted successfully.")
    else:
        print("This path is deprecated!")
    

    if os.path.exists("nova_logs/nova_log.txt"):
        os.remove("nova_logs/nova_log.txt")
        print("memoriesdir2 deleted successfully.") 
    else:
        print("Memories couldn't be deleted.")

def deleteThoughts():
    if os.path.exists("nova_logs\processing_log.txt"):
        os.remove("nova_logs\processing_log.txt")
        print("Thoughts deleted successfully.")
    else: 
        print("Thoughts not found")

main = input("Reset nova?: ").strip().lower()
if main == "yes":
    print("Nova is being reset. Please wait...")
    deleteMemories()
    deleteThoughts()
elif main == "no":
    print("exiting file")
if main == "y":
    print("Nova is being reset. Please wait...")
    deleteMemories()
    deleteThoughts()
elif main == "n":
    print("exiting file")

input("Press Enter to exit...")
    