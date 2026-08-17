from pyaccsharedmemory import accSharedMemory


asm = accSharedMemory()

data = asm.read_shared_memory()

if data is None:
    print("No ACC shared memory detected.")
else:
    print("ACC shared memory connected.")
    print()

    print("Speed:", data.Physics.speed_kmh, "km/h")
    print("Throttle:", data.Physics.gas)
    print("Brake:", data.Physics.brake)
    print("RPM:", data.Physics.rpm)
    print("Gear:", data.Physics.gear)

    print()
    print(
        "Normalized track position:",
        data.Graphics.normalized_car_position
    )

    
    print(
        "Player car ID:",
        data.Graphics.player_car_id
    )

    car_index = None

    for i in range(data.Graphics.active_cars):
        if data.Graphics.car_id[i] == data.Graphics.player_car_id:
            car_index = i
            break

    if car_index is not None:
        coords = data.Graphics.car_coordinates[car_index]

        print()
        print("World coordinates:")
        print("X:", coords.x)
        print("Y:", coords.y)
        print("Z:", coords.z)
    else:
        print("Player car coordinates not found.")
    
    

    

asm.close()