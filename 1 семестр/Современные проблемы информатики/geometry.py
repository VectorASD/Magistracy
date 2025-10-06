def distance(A, B):
    return hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2])

def intersect_unit_sphere(cam_x, cam_y, cam_z, px, py, pz):
    # Направление луча
    dx = px - cam_x
    dy = py - cam_y
    dz = pz - cam_z

    # Нормализация
    length = (dx * dx + dy * dy + dz * dz) ** 0.5
    dx /= length
    dy /= length
    dz /= length

    # Коэффициенты квадратного уравнения
    b = 2 * (cam_x * dx + cam_y * dy + cam_z * dz)
    c = cam_x ** 2 + cam_y ** 2 + cam_z ** 2 - 1
    discriminant = b ** 2 - 4 * c

    if discriminant < 0:
        return () # Нет пересечений

    if discriminant:
        sqrt_d = discriminant ** 0.5
        t1 = (-b - sqrt_d) / 2
    else: t1 = -b / 2

    first = (cam_x + t1 * dx, cam_y + t1 * dy, cam_z + t1 * dz)

    if discriminant:
        t2 = (-b + sqrt_d) / 2
        second = (cam_x + t2 * dx, cam_y + t2 * dy, cam_z + t2 * dz)
        return (first, second)
    return (first,)
