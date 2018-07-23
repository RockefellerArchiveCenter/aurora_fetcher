from django.db import models


class AccessionNumber(models.Model):
    segment_1 = models.CharField(max_length=4)
    segment_2 = models.CharField(max_length=3, null=True, blank=True)
    segment_3 = models.CharField(max_length=3, null=True, blank=True)
    segment_4 = models.CharField(max_length=3, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True)
    last_modified_time = models.DateTimeField(auto_now=True)
    in_archivesspace = models.BooleanField()

    def __str__(self):
        if self.segment_4:
            return '{0}.{1}.{2}.{3}'.format(self.segment_1, self.segment_2, self.segment_3, self.segment_4)
        elif self.segment_3:
            return '{0}.{1}.{2}'.format(self.segment_1, self.segment_2, self.segment_3)
        else:
            return '{0}.{1}'.format(self.segment_1, self.segment_2)
