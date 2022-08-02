def check_goldbach_for_num(n,primes_set):
    '''gets an even integer- n, and a set of primes- primes_set. Returns whether there're two primes which their sum is n'''

    return any(((p < n) and ((n - prime) in primes_set)) for prime in primes_set)

