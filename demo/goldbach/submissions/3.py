def check_goldbach_for_num(n, primes_set):
    return any(i in primes_set and n-i in primes_set for i in range(2, n//2+1))

