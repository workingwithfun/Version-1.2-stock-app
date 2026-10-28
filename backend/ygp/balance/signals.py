"""from django.db.models.signals import pre_save
from django.dispatch import receiver
from balance.models import CompanySymbol, Equity, MCAPData

@receiver(pre_save, sender=CompanySymbol)
def update_related_symbols(sender, instance, **kwargs):
    
    #When CompanySymbol.symbol changes → update symbol fields in other models.
    
    if not instance.pk:
        return  # new object, not update

    try:
        old = CompanySymbol.objects.get(pk=instance.pk)
    except CompanySymbol.DoesNotExist:
        return

    old_symbol = old.symbol
    new_symbol = instance.symbol

    if old_symbol == new_symbol:
        return

    print(f"🔄 Symbol updated: {old_symbol} → {new_symbol}")

    # Update Equity.symbol only if it exists
    Equity.objects.filter(symbol=old_symbol).update(symbol=new_symbol)

    # Update MCAPData (if still has plain symbol field)
    if hasattr(MCAPData, "symbol"):
        MCAPData.objects.filter(symbol=old_symbol).update(symbol=new_symbol)

    print("✅ Related model symbols updated")
"""