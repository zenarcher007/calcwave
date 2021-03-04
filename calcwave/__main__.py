def main(argv = None):
  try:
    from calcwave import calcwave as cw
    cw.main()
  except ModuleNotFoundError:
    # Run the dependency wizard
    from calcwave import dependencyWizard as dWizard
    dWizard.main()
    
    # Run calcwave again:
    from calcwave import calcwave as cw
    cw.main()

if __name__ == "__main__":
  main()
 #audiostudio()
 
