def check_goldbach_for_num(n,primes_set):
    '''gets an even integer- n, and a set of primes- primes_set. Returns whether there're two primes which their sum is n'''

    relevant_primes_set={p for p in primes_set if p<n}

    return any((n-prime) in  relevant_primes_set for prime in primes_set)

